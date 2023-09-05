import cocotb
from cocotb_coverage.crv import *
from cocotb.triggers import FallingEdge ,Timer , RisingEdge
from cocotb.clock import Clock
from cocotb.handle import Force
import warnings
warnings.filterwarnings("ignore")
import pyuvm
from pyuvm import *
from tinyalu_utils import Ops, alu_prediction, logger, get_int


class transactions(Randomized,uvm_component):
   def __init__(self ,name = "TRANSACTIONS"):
      Randomized.__init__(self)
      self.name = name
      self.a   = 0
      self.b   = 0
      self.op  = 0
      self.c   = 0
      self.out = 0
      self.add_rand("a" , list(range(0, 16)))
      self.add_rand("b" , list(range(0, 16)))
      self.add_rand("op", list(range(0, 4 )))
   def Generate_Values (self):
      self.a   = random.randrange(0,16)
      self.b   = random.randrange(0,16)
      self.op  = random.randrange(0,4)
   def print (self):
      logger.info("the Value of b is   " + str(self.a  ))
      logger.info("the Value of b is   " + str(self.b  ))
      logger.info("the Value of c is   " + str(self.c  ))
      logger.info("the Value of op is  " + str(self.op ))
      logger.info("the Value of out is " + str(self.out))
   def Copy_Items (self,transaction_object):
      self.a   = transaction_object.a
      self.b   = transaction_object.b
      self.c   = transaction_object.c
      self.op  = transaction_object.op
      self.out = transaction_object.out

class generator (uvm_component) :

    def build_phase(self,name="GENERATOR"):

        self.trans_item_sent = transactions()
        self.queue = cocotb.queue.Queue()


    async def run_phase(self):

        self.logger.info(f"{self.get_name()} run phase")
        self.raise_objection()
        for loob_variable in range(10):
            self.trans_item_sent.randomize()
            self.logger.info("[Generator] Loop: create next item  " + str(loob_variable))
            await self.queue.put(self.trans_item_sent)
            self.logger.info("[Generator] Sending To The Driver..... ")
            self.logger.info("[Generator] Wait for driver to be done ")
            await Timer(5, units="ns")
        self.drop_objection()

class driver (uvm_component) :

    def build_phase(self,name="DRIVER"):
        self.logger.info(f"{self.get_name()} build_phase")
        self.queue1 = cocotb.queue.Queue()
        self.trans_item_reciever = transactions()
        self.dut_driver = cocotb.top
        self.event_monitor = Event(name=None)

    async def run_phase(self):
        self.logger.info(f"{self.get_name()} run phase")
        while (True):
            self.logger.info("[Driver] waiting for item ...")
            self.trans_item_reciever = await self.queue1.get()
            self.logger.info("          [Driver] Recieved items is  ...")
            self.trans_item_reciever.print()
            self.logger.info("[Driver] Driver Is Sending To Dut Module Now ...")
            self.dut_driver.a.value = self.trans_item_reciever.a
            self.dut_driver.b.value = self.trans_item_reciever.b
            self.dut_driver.op.value = self.trans_item_reciever.op
            self.event_monitor.set()

class monitor (uvm_component) :

    def build_phase(self,name="MONITOR"):
        self.logger.info(f"{self.get_name()} build_phase")
        self.trans_item_monitor = transactions()
        self.monitor_done = Event(name=None)
        self.dut_monitor = cocotb.top
        self.queuem = cocotb.queue.Queue()

    async def run_phase(self):
        self.logger.info(f"{self.get_name()} run phase")
        while (True):
            self.monitor_done.clear()
            await Timer(3, units="ns")
            self.logger.info("      [Monitor] waiting for item ...")
            self.trans_item_monitor.a = self.dut_monitor.a
            self.trans_item_monitor.b = self.dut_monitor.b
            self.trans_item_monitor.c = self.dut_monitor.c
            self.trans_item_monitor.op = self.dut_monitor.op
            self.trans_item_monitor.out = self.dut_monitor.out
            await self.queuem.put(self.trans_item_monitor)
            self.logger.info("      [Monitor] Item Has Been Recieved From Dut Module ...")
            self.trans_item_monitor.print()
            await Timer(1, units="ns")
            await self.monitor_done.wait()

class scoreboard (uvm_component) :

    def build_phase(self, name="SCOREBOARD"):
        self.logger.info(f"{self.get_name()} build_phase")
        self.index = 0
        self.test_item   = transactions()
        self.golden_item = transactions()
        self.Binary_Golden_item = 0b0
        self.Binary_Golden_item_C = 0
        self.Binary_Golden_item_Out = 0
        self.num_passes = 0
        self.num_failure = 0
        self.Bugs_List = []
        self.my_Unique_List = []
        self.drv_box = cocotb.queue.Queue()

    async def run_phase(self):
        self.logger.info(f"{self.get_name()} run phase")
        while (True):
            self.logger.info("[Score Board] waiting for item ...")
            self.test_item = await self.drv_box.get()
            self.golden_item.Copy_Items(self.test_item)
            self.logger.info("[Score Board] Recieved items is  ...")
            self.test_item.print()
            if (str(self.test_item.op) == str("00")):
                self.index = int((str(self.test_item.a) + str(self.test_item.b) + str(self.test_item.op)))
                self.Binary_Golden_item = bin(int(self.golden_item.a) + int(self.golden_item.b))[2:].zfill(5)
                self.logger.info(
                    "***************************** Printing Depuging Elements ***************************** ")
                self.logger.info(self.Binary_Golden_item)
                self.Binary_Golden_item_C = str(self.Binary_Golden_item[0])
                self.logger.info(self.Binary_Golden_item_C)
                self.Binary_Golden_item_Out = str(self.Binary_Golden_item[1:])
                self.logger.info(self.Binary_Golden_item_Out)
                if ((self.Binary_Golden_item_Out != str(self.test_item.out)) or (
                        self.Binary_Golden_item_C != str(self.test_item.c))):
                    self.logger.info(
                        "*************************** Test Case Adding Hase Failed *************************** ")
                    self.Bugs_List.append(self.index)
                    self.logger.info("Expected Output and Carry is : ")
                    self.logger.info(self.Binary_Golden_item_Out)
                    self.logger.info(self.Binary_Golden_item_C)
                    self.num_failure = self.num_failure + 1
                else:
                    self.logger.info(
                        "*************************** Test Case Adding Hase succeeded *************************** ")
                    self.num_passes = self.num_passes + 1

            elif (str(self.test_item.op) == str("01")):
                self.index = int((str(self.test_item.a) + str(self.test_item.b) + str(self.test_item.op)))
                self.Binary_Golden_item = bin(int(self.golden_item.a) ^ int(self.golden_item.b))[2:].zfill(5)
                self.logger.info(
                    "***************************** Printing Depuging Elements ***************************** ")
                self.logger.info(self.Binary_Golden_item)
                self.Binary_Golden_item_C = str(self.Binary_Golden_item[0])
                self.logger.info(self.Binary_Golden_item_C)
                self.Binary_Golden_item_Out = str(self.Binary_Golden_item[1:])
                self.logger.info(self.Binary_Golden_item_Out)
                if ((self.Binary_Golden_item_Out != str(self.test_item.out)) or (
                        self.Binary_Golden_item_C != str(self.test_item.c))):
                    self.logger.info(
                        "*************************** Test Case Xor Hase Failed **************************** ")
                    self.Bugs_List.append(self.index)
                    self.logger.info("Expected Output and Carry is : ")
                    self.logger.info(self.Binary_Golden_item_Out)
                    self.logger.info(self.Binary_Golden_item_C)
                    self.num_failure = self.num_failure + 1
                else:
                    self.logger.info(
                        "*************************** Test Case Xor Hase succeeded *************************** ")
                    self.num_passes = self.num_passes + 1


            elif (str(self.test_item.op) == str("10")):
                self.index = int((str(self.test_item.a) + str(self.test_item.b) + str(self.test_item.op)))
                self.Binary_Golden_item = bin(int(self.golden_item.a) & int(self.golden_item.b))[2:].zfill(5)
                self.logger.info(
                    "***************************** Printing Depuging Elements ***************************** ")
                self.logger.info(self.Binary_Golden_item)
                self.Binary_Golden_item_C = str(self.Binary_Golden_item[0])
                self.logger.info(self.Binary_Golden_item_C)
                self.Binary_Golden_item_Out = str(self.Binary_Golden_item[1:])
                self.logger.info(self.Binary_Golden_item_Out)
                if ((self.Binary_Golden_item_Out != str(self.test_item.out)) or (
                        self.Binary_Golden_item_C != str(self.test_item.c))):
                    self.logger.info(
                        "*************************** Test Case Anding Hase Failed *************************** ")
                    self.Bugs_List.append(self.index)
                    self.logger.info("Expected Output and Carry is : ")
                    self.logger.info(self.Binary_Golden_item_Out)
                    self.logger.info(self.Binary_Golden_item_C)
                    self.num_failure = self.num_failure + 1
                else:
                    self.logger.info(
                        "*************************** Test Case Anding Hase succeeded *************************** ")
                    self.num_passes = self.num_passes + 1


            elif (str(self.test_item.op) == str("11")):
                self.index = int((str(self.test_item.a) + str(self.test_item.b) + str(self.test_item.op)))
                self.Binary_Golden_item = bin(int(self.golden_item.a) | int(self.golden_item.b))[2:].zfill(5)
                self.logger.info(
                    "***************************** Printing Depuging Elements ***************************** ")
                self.logger.info(self.Binary_Golden_item)
                self.Binary_Golden_item_C = str(self.Binary_Golden_item[0])
                self.logger.info(self.Binary_Golden_item_C)
                self.Binary_Golden_item_Out = str(self.Binary_Golden_item[1:])
                self.logger.info(self.Binary_Golden_item_Out)
                if ((self.Binary_Golden_item_Out != str(self.test_item.out)) or (
                        self.Binary_Golden_item_C != str(self.test_item.c))):
                    self.logger.info("*************************** Test Case Or Hase Failed *************************** ")
                    self.Bugs_List.append(self.index)
                    self.logger.info("Expected Output and Carry is : ")
                    self.logger.info(self.Binary_Golden_item_Out)
                    self.logger.info(self.Binary_Golden_item_C)
                    self.num_failure = self.num_failure + 1
                else:
                    self.logger.info(
                        "***************************** Test Case Or Hase succeeded ***************************** ")
                    self.num_passes = self.num_passes + 1
                    self.logger.info("Expected Output and Carry is : ")
                    self.logger.info(self.Binary_Golden_item_Out)
                    self.logger.info(self.Binary_Golden_item_C)

    def report_phase(self):
        self.my_Unique_List = set(self.Bugs_List)
        self.logger.info("******************************* simulation Finished **********************************")
        self.logger.info("NUMBER OF TEST CASES WHICH HAS PASSED is : " + str(self.num_passes))
        self.logger.info("NUMBER OF TEST CASES WHICH HAS Failed is : " + str(self.num_failure))
        self.logger.info("NUMBER OF UNIQUE BUGS OF THE DESIGN IS   : " + str(len(self.my_Unique_List)))

class environment(uvm_env):

    def build_phase(self):
        self.Scoreboard = scoreboard.create("Scoreboard", self)
        self.Monitor = monitor.create("Monitor", self)
        self.Driver = driver.create("Driver", self)
        self.Generator  = generator.create("Generator", self)




    def connect_phase(self):
        self.Driver.queue1  = self.Generator.queue
        self.Monitor.queuem = self.Scoreboard.drv_box
        self.Driver.event_monitor = self.Monitor.monitor_done



@pyuvm.test()
class TestTop(uvm_test):
    def build_phase(self):
        self.logger.info(f"{self.get_name()} build_phase")
        self.Environment = environment("Environment", self)

    async def run_phase(self):
        self.raise_objection()
        self.logger.info(f"{self.get_name()} run phase")
        self.drop_objection()





