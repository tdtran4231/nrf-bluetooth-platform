from pyBusPirateLite.BitBang import *
import time, sys

# BY TED HERMAN

# see http://dangerousprototypes.com/docs/Raw-wire_(binary) for details
# on the following raw-wire Bus Pirate commands
CMD_READ_BYTE =     "\x06"
CMD_READ_BIT =      "\x07"
CMD_WRITE_BYTES =   "\x10"
CMD_CLOCK_TICKS =   "\x20"
CMD_WRITE_BITS=     "\x30"
CMD_CONFIG_PERIPH = "\x40"
CMD_SET_SPEED =     "\x60"
CMD_SET_CONFIG =    "\x80"

# an enumeration of ARM and nRF51 registers
IDCODE   = 1 
ABORT    = 2
CTRLSTAT = 3
RESEND   = 4  
SELECT   = 5 
RDBUF    = 6 
CSW      = 7     
TAR      = 8
DRW      = 9 
IDR      = 10 
CFG      = 11 
BD0      = 12 
BD1      = 13 
BD2      = 14 
BD3      = 15 
BASE     = 16
ERASEPAGE= 17
CODEPAGESIZE = 18
CODESIZE = 19
CLEN0    = 20
CONFIG   = 21
# modes of port/memory
DP       = 0
AP       = 1
FICR     = 2
UICR     = 3
SCS      = 4



class regdesc(object):
  def __init__(self,Id,Addr,Area):
    assert Area in (DP,AP,FICR,UICR)
    self.Id,self.Addr,self.Area = Id, Addr, Area 

regtable = [
  regdesc(IDCODE,0,DP), 
  regdesc(ABORT,0,DP), 
  regdesc(CTRLSTAT,4,DP), 
  regdesc(SELECT,8,DP), 
  regdesc(RDBUF,0x0c,DP), 
  regdesc(CSW,0,AP), 
  regdesc(TAR,4,AP), 
  regdesc(DRW,0x0c,AP), 
  regdesc(BASE,0xf8,AP),
  regdesc(IDR,0xfc,AP),
  regdesc(CFG,0xf4,AP),
  regdesc(BD0,0x10,AP),
  regdesc(BD1,0x14,AP),
  regdesc(BD2,0x18,AP),
  regdesc(BD3,0x1c,AP),
  regdesc(CODEPAGESIZE,0x010,FICR),
  regdesc(CODESIZE,0x014,FICR),
  regdesc(CLEN0,0x028,FICR),
  regdesc(CONFIG,0x504,UICR),
  regdesc(ERASEPAGE,0x508,UICR),
  ] 

Current = True # another enumeration for readability
banks_last = { Current: None }
tar_last = { Current: None }

'''
  Additional information on AHB-AP registers:

    The AHB-AP is selected by writing 0 to the APSEL field 
    of the SELECT register. This has to be performed
    before using the AHB-AP. 

     CSW (bits 31..0)
        bits 11-8 -- mode (must be zero)
        bit  7    -- transfer in progress (zero means idle) 
        bit  6    -- device enable
        bits 5-4  -- AddrInc (whether Auto-Increment in effect)
        bits 2-0  -- size

     TAR register - the address register for operations  

        32-bit address for debug read/write, and can auto-increment
         
     DRW register -- Data Read/Write   

        data to be written, or data read

     IDR register -- Identification Register

        To read this register, the APBANKSEL field should be set to 0xF. 
        And then IDR register can be read with address 0x0C. 

     CFG register -- Coniguration Register

        To read this register, the APBANKSEL field should be set to 0xF. 
        And then CFG register can be read with address 0x04. Bit 0 is the only 
        interesting one, it means "big endian" if 1. 


  Additional information on DP registers:

     AP ABORT (bits 31..0)
         
        bits 4..0 -- writing 1's in these bits clears various "stuck" 
                     flags on the MCU, like a reset

     CTRL/STAT (bits 31..0)
   
        many bits defined in here, see the manual for all of them;
        the program must write 1 to bits 30 and 28 before using the
        AHB-AP bank of registers

     AP SELECT register (bits 31..0)
    
        bits 31-24 -- which AP is selected
        bits 7-4   -- which 4-register bank is selected
 
     RDBUF quote from the manual:

       On a SW-DP, performing a read of RDBUF captures data 
       from the AP, presented as the result of a previous read, 
       without initiating a new AP transaction. This means that 
       reading the Read Buffer returns the result of the last AP 
       read access, without generating a new AP access.

       After you have read the Read Buffer, its contents are no longer 
       valid. The result of a second read of the Read
       Buffer is UNPREDICTABLE.  If you require the value from an AP 
       register read, that read must be followed by one of:
        -- A second AP register read, with the appropriate AP 
           selected as the current AP.
        -- A read of the DP Read Buffer.
       This second access, to the AP or the DP depending on which 
       option you use, stalls until the result of the original AP read 
       is available       

'''

B = BBIO(p="/dev/ttyUSB0",s=115200,t=5)
Otrace = list()
Debug = False 

def portwrite(value):
  if Debug and value == "\x21":
     for c in Otrace: sys.stdout.write("{0:02x}".format(ord(c)))
     sys.stdout.write("{0:02x}\n".format(ord(value)))
     Otrace[:] = []
  elif Debug: 
     for c in value: Otrace.append(c)
  B.port.write(value)

def BBclear():
  "Kind of an unknown state clearing of the BusPirate port"
  while B.port.inWaiting():
    b = B.port.read(1)

def BBgetacks(n,validate=True):
  "Consume n acks by reading the port n times"
  acklist = list()
  for i in range(n): acklist.append(B.response(1))
  # print "Acks read =", acklist
  if all(e for e in acklist): return
  sys.stdout.write("Error - not all of {0} acks were 1\n".format(n))
  sys.exit(1)

def BBgetdata(n):
  "Consume n inputs and display"
  datalist = list()
  for i in range(n): datalist.append(B.response(1))
  sys.stdout.write("{0} data items = {1}\n".format(n,datalist))

def setupPirate():
  "Establish Bus Pirate BitBang Connection"
  assert B.resetBP()
  assert B.BBmode()
  assert B.enter_rawwire()
  BBwriteGetAck("\x8a\x63\x48")    # configure Bus Pirate
  # 8a = configure 3.3v, 2-wire, LSB first 
  # 63 = set 400kHz timing
  # 48 = configure as peripherals have power 

def BBwriteGetAck(bytestr):  
  "write contents of bytestr, collect acks"
  portwrite(bytestr)
  BBgetacks(len(bytestr))

def BBwriteCmd(command):
  "write command, collect acks"
  portwrite(CMD_WRITE_BYTES)       # default is 1 byte, which is correct
  portwrite(command)
  BBgetacks(2) 
  portwrite(CMD_READ_BIT*3)
  # NOTE - ARM manual shows timing diagrams with a turnaround
  # inserted here, but is it really needed? 
  B.port.flush()
  datalist = list()
  for i in range(3): datalist.append(B.response(1))
  # if tuple(datalist) != (1,0,0):
  #    print "datalist =", datalist
  assert tuple(datalist) == (1,0,0)

def BBwriteBytes(bytestring):
  "send a string of bytes on the Bus Pirate"
  assert 0 < len(bytestring) <= 16
  command = chr( ord(CMD_WRITE_BYTES) | len(bytestring)-1 )
  portwrite(command)
  portwrite(bytestring)
  BBgetacks(1+len(bytestring)) 

def ARM_init():
  '''
  According to SiLabs Document AN0062 
   "Programming Internal Flash Over the Serial Wire Debug Interface"
  there are four steps to initialize ARM programming:
    1. perform a line reset
    2. send the JTAG-to-SWD switching sequence
    3. perform a line reset 
    4. read the ICODE register
  where a line reset is performed by clocking at least 50 cycles with
  the SWDIO line kept high 
  '''
  BBwriteBytes("\xff"*7)              # line reset
  BBwriteBytes("\x9e\xe7")            # JTAG-to-SWD (LSB first) 
  BBwriteBytes("\xff"*7)              # line reset
  BBwriteBytes("\x00")                # switch to bitbang mode 
  # R = ARMSWD_command(Register=IDCODE,DP=True,Read=True)
  R = Read(IDCODE)
  assert R == 0xbb11477

def revbits(x):
  #print "revbits of", hex(ord(x))
  x = ord(x)
  r = x & 1 
  for i in range(7):
    r = r << 1
    x = x >> 1 
    r = r | (x & 1) 
  #print "revbits result", hex(r) 
  return chr(r)
    
def ARMSWD_command(Register=0,Value=0,DP=True,Read=True):
  # Value - reverse order (LSB first) and convert to byte string
  byteString  = chr(Value & 0xff)
  byteString += chr((Value >> 8) & 0xff)
  byteString += chr((Value >> 16) & 0xff)
  byteString += chr((Value >> 24) & 0xff)
  basecmd = "\x81"
  addrbits = {0:"\x00", 4:"\x10", 8:"\x08", 0xC:"\x18"}[Register]
  dpap = "\x00"
  if not DP: dpap = "\x40"
  oper = "\x00"
  if Read:   oper = "\x20"
  parity = ord(addrbits) | ord(dpap) | ord(oper) 
  parity = chr(parity >> 3)
  if parity in ("\x00","\x0f","\x0a","\x09","\x0c","\x06","\x05","\x03"):
     parity = "\x00"
  else: parity = "\x04"
  command = ord(basecmd) | ord(parity) | ord(dpap) | ord(addrbits) | ord(oper)
  command = chr(command)
  if Read:
     BBwriteCmd(revbits(command))
     R = readWordParity()
     portwrite(chr(ord(CMD_CLOCK_TICKS)|0x01))
     BBgetacks(1) 
     return R
  else:
     BBwriteCmd(revbits(command))
     portwrite(chr(ord(CMD_CLOCK_TICKS)|0x01))
     BBgetacks(1) 
     BBwriteBytes(byteString)
     portwrite(CMD_WRITE_BITS) 
     if Parity(Value): portwrite("\x80")
     else:             portwrite("\x00")
     BBgetacks(2)

def ARMdpRead(Register=0):
  v = Register
  R = ARMSWD_command(Register=v,Value=0,DP=True,Read=True)
  if Debug: sys.stdout.write("Read of DP Register {0:02x} ".format(v))
  if Debug: sys.stdout.write("--> {0:08x}\n".format(R))
  return R

def ARMapRead(Register=0):
  v = Register
  R = ARMSWD_command(Register=v,Value=0,DP=False,Read=True)
  if Debug: sys.stdout.write("Read of AP Register {0:02x} ".format(v))
  if Debug: sys.stdout.write("--> {0:08x}\n".format(R))
  return R

def ARMdpWrite(Register=0,Value=None):
  v,w = Register,Value
  R = ARMSWD_command(Register=v,Value=w,DP=True,Read=False)
  if Debug: sys.stdout.write("Write of DP Register {0:02x} ".format(v))
  if Debug: sys.stdout.write("<-- {0:08x}\n".format(w))
  return R

def ARMapWrite(Register=0,Value=None):
  v,w = Register,Value
  R = ARMSWD_command(Register=v,Value=w,DP=False,Read=False)
  if Debug: sys.stdout.write("Write of AP Register {0:02x} ".format(v))
  if Debug: sys.stdout.write("<-- {0:08x}\n".format(w))
  return R

def Parity(word):
  parity = word
  parity = parity ^ (parity >> 16)
  parity = parity ^ (parity >> 8)
  parity = parity ^ (parity >> 4)
  parity = parity ^ (parity >> 2)
  parity = parity ^ (parity >> 1)
  return parity & 0x01

def readWordParity():
  for i in range(4): portwrite(CMD_READ_BYTE)
  portwrite(CMD_READ_BIT)
  B.port.flush()
  word = B.response(4)[::-1]
  word = sum( ord(word[i])*256**(3-i) for i in range(4) ) 
  parity = B.response(1)
  assert Parity(word) == parity
  return word

def AHB_AP_init():
  Write(ABORT,0x1e)
  Write(SELECT,0)
  Write(CTRLSTAT,0x50000000)
  R = Read(CTRLSTAT)
  assert R == 0xf0000000L
  R = Read(IDR)
  assert R == 0x4770021
  R = Read(CSW)
  Write(CSW,0x03000052)
  R = Read(CSW)
  assert R == 0x03000052

def Read(register):
  for e in regtable:   
    if e.Id == register:
      break 
  assert e.Id == register
  if e.Area == DP:
    return ARMdpRead(Register=e.Addr)
  if e.Area == AP:
    bank = e.Addr & 0xf0;
    if banks_last[Current] != bank:
      ARMdpWrite(Register=0x08,Value=bank)
      banks_last[Current] = bank
    ARMapRead(Register=(e.Addr & 0x0f))
    return ARMdpRead(Register=0x0c)
  if e.Area in (FICR,UICR):
    base = 0x10000000
    if e.Area == UICR: base = 0x10001000
    align = e.Addr & 0xfffffff0
    if tar_last[Current] != base+align: 
       Write(TAR,base+align) 
       tar_last[Current] = base+align
    if banks_last[Current] != 0x10:
      ARMdpWrite(Register=0x08,Value=0x10)
      banks_last[Current] = 0x10 
    ARMapRead(Register=(e.Addr & 0x0f))
    return Read(RDBUF)
  if e.Area == SCS:
    base = 0xE000EDF0  
    # TODO: need to do more beyond first four registers of SCS
    align = e.Addr & 0xfffffff0
    if tar_last[Current] != base+align: 
       Write(TAR,base+align) 
       tar_last[Current] = base+align
    if banks_last[Current] != 0x10:
      ARMdpWrite(Register=0x08,Value=0x10)
      banks_last[Current] = 0x10 
    ARMapRead(Register=(e.Addr & 0x0f))
    return Read(RDBUF)
  assert False

def Write(register,value):
  for e in regtable:   
    if e.Id == register:
      break 
  assert e.Id == register
  if e.Area == DP:
    return ARMdpWrite(Register=e.Addr,Value=value)
  if e.Area == AP:
    bank = e.Addr & 0xf0;
    if banks_last[Current] != bank:
      ARMdpWrite(Register=0x08,Value=bank)
      banks_last[Current] = bank
    return ARMapWrite(Register=(e.Addr & 0x0f),Value=value)
  if e.Area in (FICR,UICR):
    base = 0x10000000
    if e.Area == UICR: base = 0x10001000
    align = e.Addr & 0xfffffff0
    if tar_last[Current] != base+align: 
       Write(TAR,base+align) 
       tar_last[Current] = base+align
    if banks_last[Current] != 0x10:
      ARMdpWrite(Register=0x08,Value=0x10)
      banks_last[Current] = 0x10 
    return ARMapWrite(Register=(e.Addr & 0x0f),Value=value)
  if e.Area == SCS:
    base = 0xE000EDF0  
    # TODO: need to do more beyond first four registers of SCS
    align = e.Addr & 0xfffffff0
    if tar_last[Current] != base+align: 
       Write(TAR,base+align) 
       tar_last[Current] = base+align
    if banks_last[Current] != 0x10:
      ARMdpWrite(Register=0x08,Value=0x10)
      banks_last[Current] = 0x10 
    return ARMapWrite(Register=(e.Addr & 0x0f),Value=value)
  assert False

def readFlash():

  Memory = list() 
  zerocount = page = 0
  building = True

  while building:
    
    # ARMapWrite(Register=TAR,Value=page)
    Write(TAR,page)
    Page = list()
    while len(Page) < 1024:
      # ARMapRead(Register=DRW)
      R = Read(DRW)
      # R = ARMdpRead(Register=RDBUF)
      # R = Read(RDBUF)
      # add bytes in reverse order, to image
      Page.append(chr(R&0xff))
      Page.append(chr((R>>8)&0xff))
      Page.append(chr((R>>16)&0xff))
      Page.append(chr((R>>24)&0xff))

    if all(c=="\xff" for c in Page): building = False
    sys.stdout.write("Got page {0:08x}\n".format(page))
    page += 1024
    Memory.extend(Page)

  ffcount = 0
  for i in range(-1,-len(Memory),-1):
    if Memory[i] != "\xff": break
    ffcount += 1

  Memory = Memory[:len(Memory)-1-ffcount]
  return ''.join(Memory)

setupPirate()
ARM_init()
AHB_AP_init()
print "CODEPAGESIZE =", Read(CODEPAGESIZE)
print "CODESIZE =", Read(CODESIZE)
print "CLEN0 =", Read(CLEN0)
print "CONFIG =", Read(CONFIG)
F = open("flashread.dat",'wb') 
F.write(readFlash())
F.close()
'''
Sequence of commands is approximately 

SWD: write dp 0 = 0000001e (force abort, bits covering flags)
SWD: write dp 8 = 00000000 (write select := 0, selecting AHB-AP bank)
DP: write dp 00000004 = 50000000 (write CTRL/STATUS bits 28 and 30 to use AHB-AP?)
SWD: write dp 4 = 50000000
SWD: read dp 4 (1 words)... (read CTRL/STATUS, validating)
SWD: read  dp 4 < f0000000
DP: read dp 00000004 < f0000000
AP: all systems up (comment: all the prep work done to use AHB-AP)
DP: write dp 00000008 = 000000f0  (write select to choose another bank in AHB-AP)  
SWD: write dp 8 = 000000f0
SWD: read ap c (1 words)... (read IDR)
SWD: read  ap c < 04770021
DP: read ap 0000000c < 04770021 
AP: 0 read 000000fc < 04770021 (0xfc is address of IDR)
AP::IDR = 0x04770021
SWD: read ap c (1 words)... (read it again, why?)
SWD: read  ap c < 04770021
DP: read ap 0000000c < 04770021
AP: 0 read 000000fc < 04770021
AP::IDR = 0x04770021
AP::IDR.mem? = 0x00000001  (there's a bit MEM in IDR, investigate further?)
AP: initializing memap 0
DP: write dp 00000008 = 00000000 (write select to revert back to main AHB-AP)
SWD: write dp 8 = 00000000
SWD: read ap 0 (1 words)... (read CSW reg)
SWD: read  ap 0 < 03000040
DP: read ap 00000000 < 03000040
AP: 0 read 00000000 < 03000040
AP::CSW = 0x03000040
AP: write: CSW.Size = 0x00000002 (write CSW.Size = 2)
MemAP::CSW = 0x03000042
AP::CSW = 0x03000042
AP: write:CSW.AddrInc = 0x00000001 (write CSW.AddrInc bits = 1)
MemAP::CSW = 0x03000052
MemAP::CSW.Mode = 0000000000 (write CSW.Mode = 0)
MemAP::CSW = 0x03000052
AP: 0 write 00000000 = 03000052
DP: write ap 00000000 = 03000052
SWD: write ap 0 = 03000052
DP: write dp 00000008 = 000000f0 (write again Select = IDR bank)
SWD: write dp 8 = 000000f0
SWD: read ap 4 (1 words)... (read CFG register, since we are in IDR bank)
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 000000f4 < 00000000 (0 in bit 31 means little-endian)
MemAP::CFG = 0000000000
MemAP::CFG.endian = 0000000000
AP: found AP 0, #<Adiv5::AP::IDR:0xa3179dc>, mem: true
SWD: read ap c (1 words)... (read IDR again)
SWD: read  ap c < 04770021
DP: read ap 0000000c < 04770021
AP: 0 read 000000fc < 04770021
AP::IDR = 0x04770021
AP: 0 write 00000004 (write 0x4 into maybe CSW ? Unsure) 
DP: write dp 00000008 = 00000000 (write select revert back to main AHB-AP)
SWD: write dp 8 = 00000000 (write 0 into SELECT)  
DP: write ap 00000004 = e000ed00 (write 0xE000ED00 into TAR) 
SWD: write ap 4 = e000ed00
SWD: read ap c (1 words)... (read DRW reg)
SWD: read  ap c < 410cc200
DP: read ap 0000000c < 410cc200
AP: 0 read 0000000c < 410cc200
AP: 0 write 00000004 = 10000010 (write 0x10000010 into TAR)
DP: write ap 00000004 = 10000010
SWD: write ap 4 = 10000010
SWD: read ap c (1 words)... (read DRW reg)
SWD: read  ap c < 00000400
DP: read ap 0000000c < 00000400
AP: 0 read 0000000c < 00000400
NRF51::FICR = 0x00000400 (comment: FICR discovered)
       See https://devzone.nordicsemi.com/question/31331/uicr-ficr-in-linux/ for a clue about this
AP: 0 write 00000004 = 10000034 (write 0x1000034 into TAR)
DP: write ap 00000004 = 10000034
SWD: write ap 4 = 10000034
SWD: read ap c (1 words)... (read DRW reg)
SWD: read  ap c < 00000002
DP: read ap 0000000c < 00000002
AP: 0 read 0000000c < 00000002
NRF51::FICR = 0x00000002 (command another part of FICR discovered)
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010 (write 0x10 into SELECT)
                  *** This is done to have access to registers BD0--BD3, four
                  registers that allow for direct access to memory pointed to
                  by TAR
SWD: read ap 8 (1 words)... (read register at 0x18, which is BD2)
       See IHI0031A ARM Debug Interface, page 11-9, which defines BD2 as 
       (TAR[31:4]<<4) + 0x8, which allows for direct reading of memory
SWD: read  ap 8 < 00002000 
DP: read ap 00000008 < 00002000
AP: 0 read 00000018 < 00002000
NRF51::FICR = 0x00002000 (yet another FICR discovery)
SWD: read ap c (1 words)... (read 0x1c, which is BD3)
SWD: read  ap c < 00002000
DP: read ap 0000000c < 00002000
AP: 0 read 0000001c < 00002000
NRF51::FICR = 0x00002000 (continued FICR probing)
AP: 0 write 00000004 = 10000014 (write 0x1000014 into 0x10, which is BD0)
        So it looks like this writes into location 0x10000010 in flash?
DP: write dp 00000008 = 00000000 (switch back to bank 0, main AHB-AP) I
SWD: write dp 8 = 00000000
DP: write ap 00000004 = 10000014 (are we still in the BD bank??)
SWD: write ap 4 = 10000014
SWD: read ap c (1 words)... (read DRW)
SWD: read  ap c < 00000100
DP: read ap 0000000c < 00000100
AP: 0 read 0000000c < 00000100
NRF51::FICR = 0x00000100 (continued FICR probing)
DP: write dp 00000008 = 00000010 (switch back to BD bank)
SWD: write dp 8 = 00000010
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < 00000400 (read BD0)
DP: read ap 00000000 < 00000400
AP: 0 read 00000010 < 00000400
NRF51::FICR = 0x00000400 (continued FICR probing)
DP: write dp 00000008 = 000000f0 (switch to the 0xf bank)
SWD: write dp 8 = 000000f0
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < f0000003 (read 0xf8, which is the debug BASE register)
DP: read ap 00000008 < f0000003
AP: 0 read 000000f8 < f0000003
MemAP::BASE = 0xf0000003
MemAP::BASE = 0xf0000003
MemAP::BASE = 0xf0000003
MemAP::BASE.format? = 0x00000001
MemAP::BASE = 0xf0000003
MemAP::BASE.present? = 0x00000001
MemAP::BASE = 0xf0000003
MemAP::BASE.BASEADDR = 0xf0000000
AP: Adiv5::DebugDevice at f0000000 (discoveries about BASE)
AP: 0 write 00000004 = f0000ff0 (write into TAR, 0xf000ff0)
DP: write dp 00000008 = 00000000 (switch back to main AHB-AP)
SWD: write dp 8 = 00000000
DP: write ap 00000004 = f0000ff0 (write into TAR) 
SWD: write ap 4 = f0000ff0
SWD: read ap c (4 words)... (read DRW four words)
SWD: read  ap c < 0000000d 00000010 00000005 000000b1
DP: read ap 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: device component class: rom  (apparently these values mean something)
AP: 0 write 00000004 = f0000fd0 (write into TAR 0xf0000fd0)
DP: write ap 00000004 = f0000fd0
SWD: write ap 4 = f0000fd0
SWD: read ap c (1 words)... (read DRW)
SWD: read  ap c < 00000002
DP: read ap 0000000c < 00000002
AP: 0 read 0000000c < 00000002
DebugDevice = 0x00000002 (this discovered DebugDevice)
DP: write dp 00000008 = 00000010 (switch to BD register bank)
SWD: write dp 8 = 00000010 
SWD: read ap 4 (1 words)... (read BD1)
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
DebugDevice = 0000000000 (more about DebugDevice)
SWD: read ap 8 (1 words)... (read BD2)
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
DebugDevice = 0000000000 (more about DebugDevice)
SWD: read ap c (1 words)... (read BD3)
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
DebugDevice = 0000000000 (more about DebugDevice)
AP: device size: 4096 (somehow all of this discovered device size, etc)
AP: Adiv5::ROMTable at f0000000
AP: 0 write 00000004 = f0000ff0 (write into CSW again ??)
DP: write dp 00000008 = 00000000 (switch back to main AHB-AP)
SWD: write dp 8 = 00000000
DP: write ap 00000004 = f0000ff0 (write into TAR)   
SWD: write ap 4 = f0000ff0
SWD: read ap c (4 words)... (read DRW four words)
SWD: read  ap c < 0000000d 00000010 00000005 000000b1
DP: read ap 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: device component class: rom (discovered ROM)
AP: 0 write 00000004 = f0000fd0 (write into TAR)
DP: write ap 00000004 = f0000fd0
SWD: write ap 4 = f0000fd0
SWD: read ap c (1 words)... (read DRW)
SWD: read  ap c < 00000002
DP: read ap 0000000c < 00000002
AP: 0 read 0000000c < 00000002
ROMTable = 0x00000002 (found ROMTable)
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010 (switch back to BD bank)
SWD: read ap 4 (1 words)... (read BD1)
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
ROMTable = 0000000000 (found ROMTable)
SWD: read ap 8 (1 words)... (read BD2)
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
ROMTable = 0000000000
SWD: read ap c (1 words)... (read BD3)
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
ROMTable = 0000000000
AP: device size: 4096 (again, discovered device size)
AP: 0 write 00000004 = f0000fcc (writing to BD1)
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = f0000fcc 
SWD: write ap 4 = f0000fcc
SWD: read ap c (1 words)... (read BD2)
SWD: read  ap c < 00000001
DP: read ap 0000000c < 00000001
AP: 0 read 0000000c < 00000001
ROMTable = 0x00000001
AP: 0 write 00000004 = f0000000
DP: write ap 00000004 = f0000000
SWD: write ap 4 = f0000000
SWD: read ap c (1 words)...
SWD: read  ap c < f00ff003
DP: read ap 0000000c < f00ff003
AP: 0 read 0000000c < f00ff003
ROMTable = 0xf00ff003
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < f00ff003
DP: read ap 00000000 < f00ff003
AP: 0 read 00000010 < f00ff003
ROMTable = 0xf00ff003
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < f00ff003
DP: read ap 00000000 < f00ff003
AP: 0 read 00000010 < f00ff003
ROMTable = 0xf00ff003
AP: rom table entry f00ff003
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < f00ff003
DP: read ap 00000000 < f00ff003
AP: 0 read 00000010 < f00ff003
ROMTable = 0xf00ff003
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < f00ff003
DP: read ap 00000000 < f00ff003
AP: 0 read 00000010 < f00ff003
ROMTable = 0xf00ff003
AP: Adiv5::DebugDevice at e00ff000
AP: 0 write 00000004 = e00ffff0
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e00ffff0
SWD: write ap 4 = e00ffff0
SWD: read ap c (4 words)...
SWD: read  ap c < 0000000d 00000010 00000005 000000b1
DP: read ap 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: device component class: rom
AP: 0 write 00000004 = e00fffd0
DP: write ap 00000004 = e00fffd0
SWD: write ap 4 = e00fffd0
SWD: read ap c (1 words)...
SWD: read  ap c < 00000004
DP: read ap 0000000c < 00000004
AP: 0 read 0000000c < 00000004
Adiv5::DebugDevice = 0x00000004
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
DebugDevice = 0000000000
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
DebugDevice = 0000000000
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
DebugDevice = 0000000000
AP: device size: 4096
AP: Adiv5::ROMTable at e00ff000
AP: 0 write 00000004 = e00ffff0
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e00ffff0
SWD: write ap 4 = e00ffff0
SWD: read ap c (4 words)...
SWD: read  ap c < 0000000d 00000010 00000005 000000b1
DP: read ap 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 00000010, 00000005, 000000b1
AP: device component class: rom
AP: 0 write 00000004 = e00fffd0
DP: write ap 00000004 = e00fffd0
SWD: write ap 4 = e00fffd0
SWD: read ap c (1 words)...
SWD: read  ap c < 00000004
DP: read ap 0000000c < 00000004
AP: 0 read 0000000c < 00000004
ROMTable = 0x00000004
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
ROMTable = 0000000000
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
ROMTable = 0000000000
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
ROMTable = 0000000000
AP: device size: 4096
AP: 0 write 00000004 = e00fffcc
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e00fffcc
SWD: write ap 4 = e00fffcc
SWD: read ap c (1 words)...
SWD: read  ap c < 00000001
DP: read ap 0000000c < 00000001
AP: 0 read 0000000c < 00000001
ROMTable = 0x00000001
AP: 0 write 00000004 = e00ff000
DP: write ap 00000004 = e00ff000
SWD: write ap 4 = e00ff000
SWD: read ap c (1 words)...
SWD: read  ap c < fff0f003
DP: read ap 0000000c < fff0f003
AP: 0 read 0000000c < fff0f003
ROMTable = 0xfff0f003
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < fff0f003
DP: read ap 00000000 < fff0f003
AP: 0 read 00000010 < fff0f003
ROMTable = 0xfff0f003
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < fff0f003
DP: read ap 00000000 < fff0f003
AP: 0 read 00000010 < fff0f003
ROMTable = 0xfff0f003
AP: rom table entry fff0f003
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < fff0f003
DP: read ap 00000000 < fff0f003
AP: 0 read 00000010 < fff0f003
ROMTable = 0xfff0f003
SWD: read ap 0 (1 words)...
SWD: read  ap 0 < fff0f003
DP: read ap 00000000 < fff0f003
AP: 0 read 00000010 < fff0f003
ROMTable = 0xfff0f003
AP: Adiv5::DebugDevice at e000e000
AP: 0 write 00000004 = e000eff0
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e000eff0
SWD: write ap 4 = e000eff0
SWD: read ap c (4 words)...
SWD: read  ap c < 0000000d 000000e0 00000005 000000b1
DP: read ap 0000000c < 0000000d, 000000e0, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 000000e0, 00000005, 000000b1
AP: device component class: generic_ip
AP: 0 write 00000004 = e000efd0
DP: write ap 00000004 = e000efd0
SWD: write ap 4 = e000efd0
SWD: read ap c (1 words)...
SWD: read  ap c < 00000004
DP: read ap 0000000c < 00000004
AP: 0 read 0000000c < 00000004
DebugDevice = 0x00000004
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
DebugDevice = 0000000000
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
DebugDevice = 0000000000
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
DebugDevice = 0000000000
AP: device size: 4096
AP: 0 write 00000004 = e00ff004
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e00ff004
SWD: write ap 4 = e00ff004
SWD: read ap c (1 words)...
SWD: read  ap c < fff02003
DP: read ap 0000000c < fff02003
AP: 0 read 0000000c < fff02003
ROMTable = 0xfff02003
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < fff02003
DP: read ap 00000004 < fff02003
AP: 0 read 00000014 < fff02003
ROMTable = 0xfff02003
AP: rom table entry fff02003
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < fff02003
DP: read ap 00000004 < fff02003
AP: 0 read 00000014 < fff02003
ROMTable = 0xfff02003
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < fff02003
DP: read ap 00000004 < fff02003
AP: 0 read 00000014 < fff02003
ROMTable = 0xfff02003
AP: Adiv5::DebugDevice at e0001000
AP: 0 write 00000004 = e0001ff0
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e0001ff0
SWD: write ap 4 = e0001ff0
SWD: read ap c (4 words)...
SWD: read  ap c < 0000000d 000000e0 00000005 000000b1
DP: read ap 0000000c < 0000000d, 000000e0, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 000000e0, 00000005, 000000b1
AP: device component class: generic_ip
AP: 0 write 00000004 = e0001fd0
DP: write ap 00000004 = e0001fd0
SWD: write ap 4 = e0001fd0
SWD: read ap c (1 words)...
SWD: read  ap c < 00000004
DP: read ap 0000000c < 00000004
AP: 0 read 0000000c < 00000004
DebugDevice = 0x00000004
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
DebugDevice = 0000000000
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
DebugDevice = 0000000000
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
Adiv5::DebugDevice = 0000000000
AP: device size: 4096
AP: 0 write 00000004 = e00ff008
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e00ff008
SWD: write ap 4 = e00ff008
SWD: read ap c (1 words)...
SWD: read  ap c < fff03003
DP: read ap 0000000c < fff03003
AP: 0 read 0000000c < fff03003
ROMTable = 0xfff03003
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < fff03003
DP: read ap 00000008 < fff03003
AP: 0 read 00000018 < fff03003
ROMTable = 0xfff03003
AP: rom table entry fff03003
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < fff03003
DP: read ap 00000008 < fff03003
AP: 0 read 00000018 < fff03003
ROMTable = 0xfff03003
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < fff03003
DP: read ap 00000008 < fff03003
AP: 0 read 00000018 < fff03003
ROMTable = 0xfff03003
AP: Adiv5::DebugDevice at e0002000
AP: 0 write 00000004 = e0002ff0
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e0002ff0
SWD: write ap 4 = e0002ff0
SWD: read ap c (4 words)...
SWD: read  ap c < 0000000d 000000e0 00000005 000000b1
DP: read ap 0000000c < 0000000d, 000000e0, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 000000e0, 00000005, 000000b1
AP: device component class: generic_ip
AP: 0 write 00000004 = e0002fd0
DP: write ap 00000004 = e0002fd0
SWD: write ap 4 = e0002fd0
SWD: read ap c (1 words)...
SWD: read  ap c < 00000004
DP: read ap 0000000c < 00000004
AP: 0 read 0000000c < 00000004
DebugDevice = 0x00000004
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
DebugDevice = 0000000000
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
DebugDevice = 0000000000
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
DebugDevice = 0000000000
AP: device size: 4096
AP: 0 write 00000004 = e00ff00c
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = e00ff00c
SWD: write ap 4 = e00ff00c
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000000c < 00000000
ROMTable = 0000000000
AP: 0 write 00000004 = f0000004
DP: write ap 00000004 = f0000004
SWD: write ap 4 = f0000004
SWD: read ap c (1 words)...
SWD: read  ap c < 00002003
DP: read ap 0000000c < 00002003
AP: 0 read 0000000c < 00002003
ROMTable = 0x00002003
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00002003
DP: read ap 00000004 < 00002003
AP: 0 read 00000014 < 00002003
ROMTable = 0x00002003
AP: rom table entry 00002003
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00002003
DP: read ap 00000004 < 00002003
AP: 0 read 00000014 < 00002003
ROMTable = 0x00002003
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00002003
DP: read ap 00000004 < 00002003
AP: 0 read 00000014 < 00002003
ROMTable = 0x00002003
AP: Adiv5::DebugDevice at f0002000
AP: 0 write 00000004 = f0002ff0
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = f0002ff0
SWD: write ap 4 = f0002ff0
SWD: read ap c (4 words)...
SWD: read  ap c < 0000000d 00000090 00000005 000000b1
DP: read ap 0000000c < 0000000d, 00000090, 00000005, 000000b1
AP: 0 read 0000000c < 0000000d, 00000090, 00000005, 000000b1
AP: device component class: debug
AP: 0 write 00000004 = f0002fd0
DP: write ap 00000004 = f0002fd0
SWD: write ap 4 = f0002fd0
SWD: read ap c (1 words)...
SWD: read  ap c < 00000004
DP: read ap 0000000c < 00000004
AP: 0 read 0000000c < 00000004
DebugDevice = 0x00000004
DP: write dp 00000008 = 00000010
SWD: write dp 8 = 00000010
SWD: read ap 4 (1 words)...
SWD: read  ap 4 < 00000000
DP: read ap 00000004 < 00000000
AP: 0 read 00000014 < 00000000
DebugDevice = 0000000000
SWD: read ap 8 (1 words)...
SWD: read  ap 8 < 00000000
DP: read ap 00000008 < 00000000
AP: 0 read 00000018 < 00000000
DebugDevice = 0000000000
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000001c < 00000000
DebugDevice = 0000000000
AP: device size: 4096
AP: 0 write 00000004 = f0000008
DP: write dp 00000008 = 00000000
SWD: write dp 8 = 00000000
DP: write ap 00000004 = f0000008
SWD: write ap 4 = f0000008
SWD: read ap c (1 words)...
SWD: read  ap c < 00000000
DP: read ap 0000000c < 00000000
AP: 0 read 0000000c < 00000000
ROMTable = 0000000000
AP: 0 write 00000004 = 00000000 (set TAR to zero)
DP: write ap 00000004 = 00000000
SWD: write ap 4 = 00000000
SWD: read ap c (256 words)... (read DRW for 256 words) 
SWD: read  ap c < 20004000 00000415 0000045d 0000045f 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000461 00000000 00000000 00000463 00000465 00000467 00000467 00000467 00000467 00000467 00000000 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000467 00000000 00000000 00000000 00000000 00000000 00000000 4c06b510 2b007823 4b05d107 d0022b00 e0004804 2301bf00 bd107023 20002068 00000000 00000488 4b08b508 d0032b00 49084807 bf00e000 68034807 d1002b00 4b06bd08 d0fb2b00 e7f94798 00000000 00000488 2000206c 20002068 00000000 2b004b16 4b14d100 2240469d 1a9a0292 21004692 460f468b 4a144813 f0001a12 4b0ff867 d0002b00 4b0e4798 d0002b00 20004798 00042100 480d000d d0022800 e000480c f000bf00 0020f82d f0000029 f000f8a7 46c0f811 00080000 20004000 00000000 00000000 20002068 20002084 00000000 00000000 b5104b08 2b001c04 2100d002 bf00e000 68184b05 2b006a83 4798d000 f0001c20 46c0f833 00000000 00000484 b5704b0e 1c1e2500 1ae44c0d 42a510a4 00abd004 479858f3 e7f83501 f942f000 25004b08 4c081c1e 10a41ae4 d00442a5 58f300ab 35014798 bd70e7f8 20002060 20002060 20002060 20002064 18821c03 d0024293 33017019 4770e7fa 46c0e7fe 781b4b1f d0002b01 4b1e4770 071b681b 22f0d1fa 681b4b1c d1184013 681b4b1b d01a4213 681b4b17 d1ed071b 4b1622f0 4013681b d1e72b40 681b4b14 d1e34213 228023c1 00db2101 50d105d2 2b10e7dc 4b0ed10f 4213681b 4a0dd1e8 601a4b0d 4b0d2280 601a0212 781b4b05 d0d92b01 2b30e7ca 4b05d1da 4213681b e7ecd1d6 f0000fe0 f0000fe4 f0000fe8 f0000fec c007ffdf 40000504 40006c18 22e9b570 230324a0 05e42500 50a300d2 4e3e4a3d 320450a3 4a3d50a3 320450a3 20fa50a3 f0000080 59a3f877 35012301 402bb2ed 2180d133 02c922a1 50a100d2 50a34a34 230259a3 d133402b 22a12180 00d20309 4a2f50a1 59a350a3 402b2304 2180d133 034922a1 50a100d2 50a34a29 230859a3 d133402b 22a12180 00d20389 4a2450a1 59a350a3 402b2310 2180d133 03c922a1 50a100d2 50a34a1e 2280e7c1 02d24b1c 220050e2 50e23b04 230259a3 d0cb402b 4b172280 50e20312 3b042200 59a350e2 402b2304 2280d0cb 03524b11 220050e2 50e23b04 230859a3 d0cb402b 4b0c2280 50e20392 3b042200 59a350e2 402b2310 2280d0cb 03d24b06 220050e2 50e23b04 46c0e78d 0000074c 00000504 00000754 0000050c 9001b082 2b009b01 9b01d014 3b01480a 38019301 46c046c0 46c046c0 46c046c0 46c046c0 46c046c0
DP: read ap 0000000c < 20004000, 00000415, 0000045d, 0000045f, 00000000, 00000000, 00000000, 00000000, 00000000, 00000000, 00000000, 00000461, 00000000, 00000000, 00000463, 00000465, 00000467, 00000467, 00000467, 00000467, 00000467, 00000000, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000000, 00000000, 00000000, 00000000, 00000000, 00000000, 4c06b510, 2b007823, 4b05d107, d0022b00, e0004804, 2301bf00, bd107023, 20002068, 00000000, 00000488, 4b08b508, d0032b00, 49084807, bf00e000, 68034807, d1002b00, 4b06bd08, d0fb2b00, e7f94798, 00000000, 00000488, 2000206c, 20002068, 00000000, 2b004b16, 4b14d100, 2240469d, 1a9a0292, 21004692, 460f468b, 4a144813, f0001a12, 4b0ff867, d0002b00, 4b0e4798, d0002b00, 20004798, 00042100, 480d000d, d0022800, e000480c, f000bf00, 0020f82d, f0000029, f000f8a7, 46c0f811, 00080000, 20004000, 00000000, 00000000, 20002068, 20002084, 00000000, 00000000, b5104b08, 2b001c04, 2100d002, bf00e000, 68184b05, 2b006a83, 4798d000, f0001c20, 46c0f833, 00000000, 00000484, b5704b0e, 1c1e2500, 1ae44c0d, 42a510a4, 00abd004, 479858f3, e7f83501, f942f000, 25004b08, 4c081c1e, 10a41ae4, d00442a5, 58f300ab, 35014798, bd70e7f8, 20002060, 20002060, 20002060, 20002064, 18821c03, d0024293, 33017019, 4770e7fa, 46c0e7fe, 781b4b1f, d0002b01, 4b1e4770, 071b681b, 22f0d1fa, 681b4b1c, d1184013, 681b4b1b, d01a4213, 681b4b17, d1ed071b, 4b1622f0, 4013681b, d1e72b40, 681b4b14, d1e34213, 228023c1, 00db2101, 50d105d2, 2b10e7dc, 4b0ed10f, 4213681b, 4a0dd1e8, 601a4b0d, 4b0d2280, 601a0212, 781b4b05, d0d92b01, 2b30e7ca, 4b05d1da, 4213681b, e7ecd1d6, f0000fe0, f0000fe4, f0000fe8, f0000fec, c007ffdf, 40000504, 40006c18, 22e9b570, 230324a0, 05e42500, 50a300d2, 4e3e4a3d, 320450a3, 4a3d50a3, 320450a3, 20fa50a3, f0000080, 59a3f877, 35012301, 402bb2ed, 2180d133, 02c922a1, 50a100d2, 50a34a34, 230259a3, d133402b, 22a12180, 00d20309, 4a2f50a1, 59a350a3, 402b2304, 2180d133, 034922a1, 50a100d2, 50a34a29, 230859a3, d133402b, 22a12180, 00d20389, 4a2450a1, 59a350a3, 402b2310, 2180d133, 03c922a1, 50a100d2, 50a34a1e, 2280e7c1, 02d24b1c, 220050e2, 50e23b04, 230259a3, d0cb402b, 4b172280, 50e20312, 3b042200, 59a350e2, 402b2304, 2280d0cb, 03524b11, 220050e2, 50e23b04, 230859a3, d0cb402b, 4b0c2280, 50e20392, 3b042200, 59a350e2, 402b2310, 2280d0cb, 03d24b06, 220050e2, 50e23b04, 46c0e78d, 0000074c, 00000504, 00000754, 0000050c, 9001b082, 2b009b01, 9b01d014, 3b01480a, 38019301, 46c046c0, 46c046c0, 46c046c0, 46c046c0, 46c046c0
AP: 0 read 0000000c < 20004000, 00000415, 0000045d, 0000045f, 00000000, 00000000, 00000000, 00000000, 00000000, 00000000, 00000000, 00000461, 00000000, 00000000, 00000463, 00000465, 00000467, 00000467, 00000467, 00000467, 00000467, 00000000, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000467, 00000000, 00000000, 00000000, 00000000, 00000000, 00000000, 4c06b510, 2b007823, 4b05d107, d0022b00, e0004804, 2301bf00, bd107023, 20002068, 00000000, 00000488, 4b08b508, d0032b00, 49084807, bf00e000, 68034807, d1002b00, 4b06bd08, d0fb2b00, e7f94798, 00000000, 00000488, 2000206c, 20002068, 00000000, 2b004b16, 4b14d100, 2240469d, 1a9a0292, 21004692, 460f468b, 4a144813, f0001a12, 4b0ff867, d0002b00, 4b0e4798, d0002b00, 20004798, 00042100, 480d000d, d0022800, e000480c, f000bf00, 0020f82d, f0000029, f000f8a7, 46c0f811, 00080000, 20004000, 00000000, 00000000, 20002068, 20002084, 00000000, 00000000, b5104b08, 2b001c04, 2100d002, bf00e000, 68184b05, 2b006a83, 4798d000, f0001c20, 46c0f833, 00000000, 00000484, b5704b0e, 1c1e2500, 1ae44c0d, 42a510a4, 00abd004, 479858f3, e7f83501, f942f000, 25004b08, 4c081c1e, 10a41ae4, d00442a5, 58f300ab, 35014798, bd70e7f8, 20002060, 20002060, 20002060, 20002064, 18821c03, d0024293, 33017019, 4770e7fa, 46c0e7fe, 781b4b1f, d0002b01, 4b1e4770, 071b681b, 22f0d1fa, 681b4b1c, d1184013, 681b4b1b, d01a4213, 681b4b17, d1ed071b, 4b1622f0, 4013681b, d1e72b40, 681b4b14, d1e34213, 228023c1, 00db2101, 50d105d2, 2b10e7dc, 4b0ed10f, 4213681b, 4a0dd1e8, 601a4b0d, 4b0d2280, 601a0212, 781b4b05, d0d92b01, 2b30e7ca, 4b05d1da, 4213681b, e7ecd1d6, f0000fe0, f0000fe4, f0000fe8, f0000fec, c007ffdf, 40000504, 40006c18, 22e9b570, 230324a0, 05e42500, 50a300d2, 4e3e4a3d, 320450a3, 4a3d50a3, 320450a3, 20fa50a3, f0000080, 59a3f877, 35012301, 402bb2ed, 2180d133, 02c922a1, 50a100d2, 50a34a34, 230259a3, d133402b, 22a12180, 00d20309, 4a2f50a1, 59a350a3, 402b2304, 2180d133, 034922a1, 50a100d2, 50a34a29, 230859a3, d133402b, 22a12180, 00d20389, 4a2450a1, 59a350a3, 402b2310, 2180d133, 03c922a1, 50a100d2, 50a34a1e, 2280e7c1, 02d24b1c, 220050e2, 50e23b04, 230259a3, d0cb402b, 4b172280, 50e20312, 3b042200, 59a350e2, 402b2304, 2280d0cb, 03524b11, 220050e2, 50e23b04, 230859a3, d0cb402b, 4b0c2280, 50e20392, 3b042200, 59a350e2, 402b2310, 2280d0cb, 03d24b06, 220050e2, 50e23b04, 46c0e78d, 0000074c, 00000504, 00000754, 0000050c, 9001b082, 2b009b01, 9b01d014, 3b01480a, 38019301, 46c046c0, 46c046c0, 46c046c0, 46c046c0, 46c046c0
'''

'''
From the ARMv7-M Architecture Reference Manual, section B1.2:

  ARMv7-M is a memory-mapped architecture, meaning the architecture assigns physical addresses for
  processor registers to provide:
  - event entry points, as vectors
  - system control and configuration.
  An ARMv7-M implementation maintains exception handler entry points in a table of address pointers.
  The architecture reserves address space 0xE0000000 to 0xFFFFFFFF for system-level use. ARM reserves the
  first 1MB of this system address space, 0xE0000000 to 0xE00FFFFF, as the Private Peripheral Bus (PPB).The
  assignment of the rest of the address space, from 0xE0100000, is IMPLEMENTATION DEFINED, with some
  memory attribute restrictions. See The system address map on page B3-704 for more information.
  In the PPB address space, the architecture assigns a 4KB block, 0xE000E000 to 0xE000EFFF, as the System
  Control Space (SCS). 

  Section B3.2 lays out the SCS:

  The System Control Space (SCS) is a memory-mapped 4KB address space that provides 32-bit registers for
  configuration, status reporting and control. The SCS registers divide into the following groups:
  - system control and identification
  - the CPUID processor identification space
  - system configuration and status
  - fault reporting
  - system timer, SysTick
  - Nested Vectored Interrupt Controller (NVIC)
  - Protected Memory System Architecture (PMSA)
  -  system debug.

  Table B3-3 defines the memory mapping of the SCS register groups.
     About the System Control Block on page B3-709
    System control and ID registers on page B3-709
    Debug register support in the SCS on page C1-828.
    The following sections summarize the other register groups:
       The system timer, SysTick on page B3-744
       Table B3-3 SCS address space regions
       System Control Space, address range 0xE000E000 to 0xE000EFFF
    System control and ID registers
    0xE000E000-0xE000E00F Includes the Interrupt Controller Type and Auxiliary Control registers
    0xE000ED00-0xE000ED8F System control block
    0xE000EDF0-0xE000EEFF Debug registers in the SCS
    0xE000EF00-0xE000EF8F Includes the SW Trigger Interrupt Register
    0xE000EF90-0xE000EFCF IMPLEMENTATION DEFINED
    0xE000EFD0-0xE000EFFF Microcontroller-specific ID space
    SysTick 0xE000E010-0xE000E0FF System Timer, see The system timer, SysTick on page B3-744
    NVIC 0xE000E100-0xE000ECFF External interrupt controller, see Nested Vectored Interrupt Controller,
    NVIC on page B3-750
    MPU 0xE000ED90-0xE000EDEF Memory Protection Unit, see Protected Memory System Architecture,
    PMSAv7 on page B3-761

  Then, in section C1.2, the Debug Access Port is described; there is an important register DHCSR used
  to control and monitor debugging operations, the Debug Halting Control and Status Register. So far as I 
  can tell, DHCSR is the first first of the Debug registers, hence located at 0xE000EDF0

  Fields of DHCSR
    Bits 31 .. 0
    Read of DHCSR:
      Bit 25 S_RESET_ST
      Bit 26 S_RETIRE_ST
      Bit 19 S_LOCKUP
      Bit 18 S_SLEEP
      Bit 17 S_HALT
      Bit 16 S_REGRDY
    Read and Write of DHCSR:
      Bit 5  C_SNAPSTALL
      Bit 3  C_MASKINTS
      Bit 2  C_STEP
      Bit 1  C_HALT    (set this third)
      Bit 0  C_DEBUGEN (set this second)
    Writing bits 31-16 specifies DBGKEY: (do this first)
      Software must write 0xA05F to this field to enable write accesses 
      to bits [15:0], otherwise the processor ignores the write access. 

'''
