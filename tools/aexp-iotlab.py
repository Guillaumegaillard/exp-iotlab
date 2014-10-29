#! /usr/bin/python
#---------------------------------------------------------------------------
# Start an experiment with OpenWSN sink + OpenWSN router nodes
#
# Gaillard inspired by Cedric Adjih - Inria - 2014
#---------------------------------------------------------------------------

import sys, os, re, pprint

import argparse, time, sys, random, os, pprint
import IotlabHelper
from IotlabHelper import extractNodeId, AllPossibleNodes


#---------------------------------------------------------------------------
# 
# vars
# 
#---------------------------------------------------------------------------


ExperimentName = "OpenWSN IoT-LAB experiment"
#nodeList
#borderRouterNode
#borderRouterList
#expId
SshTunnelStartPort = 3000
#routerList
#expId
#
#


ForwardedTypeList = ["openwsn", "openwsn-sink"]
TypeToFirmware = {
    "openwsn":
        "../openwsn/openwsn-fw/projects/common/03oos_openwsn_prog",
    "openwsn-sink":
        "../openwsn/openwsn-fw-sink/projects/common/03oos_openwsn_prog"
}



#---------------------------------------------------------------------------
# parser
#---------------------------------------------------------------------------

parser = argparse.ArgumentParser(
    description = ExperimentName
)
IotlabHelper.parserAddTypicalArgs(parser, "Gaillard_OpenWSN_M3_REST")
args = parser.parse_args()

#---------------------------------------------------------------------------
# launch  experiment
#---------------------------------------------------------------------------

iotlabHelper, exp = IotlabHelper.ensureExperimentFromArgs(args)
exp.makeLastSymLink() # XXX: cannot run multiple simultaneous exp. with this
#Find expID
lastExpLink = os.readlink(IotlabHelper.LastExpSymLink)
rExpId = re.compile(IotlabHelper.ExpTemplateDir.replace("%s", "([0-9]+)"))
mExpId = rExpId.search(lastExpLink)
if mExpId == None:
    raise RuntimeError("Cannot parse %s" % IotlabHelper.LastExpSymLink,
                       (IotlabHelper.ExpTemplateDir, lastExpLink))
expId = int(mExpId.group(1))


#--------------------------------------------------
# Flash nodes
#--------------------------------------------------

nodeList = exp.getNodeList()
currentNodeList = nodeList[:]

#Flash sink
#def doNodeCmd(self, cmd, nodeList = AllList, firmwareData = None):
#def doNodeCmdUpdate(self, tentativeNodeList, firmwareData):
#IotlabHelper.
flashedSinkList, currentNodeList = exp.safeFlashNodes(TypeToFirmware["openwsn-sink"], 1, currentNodeList, 
                       verbose=True, shouldTryOnce=False)

exp.recordFlashedNodes("openwsn-sink", flashedSinkList, TypeToFirmware["openwsn-sink"])

for address in flashedSinkList:
    if address in currentNodeList:
        currentNodeList.remove(address)
                                
flashedNodeList, currentNodeList = exp.safeFlashNodes(TypeToFirmware["openwsn"], AllPossibleNodes, currentNodeList, 
                       verbose=True, shouldTryOnce=False)

exp.recordFlashedNodes("openwsn", flashedNodeList, TypeToFirmware["openwsn"])

for address in flashedNodeList:
    if address in currentNodeList:
        currentNodeList.remove(address)                       
                       

             

#--------------------------------------------------
# Save scenario
#--------------------------------------------------

expInfo = exp.getPersistentInfo()
expInfo["name"] = ExperimentName
expInfo["args"] = vars(args)
expInfo["failed"] = currentNodeList
exp.savePersistentInfo(expInfo)


#---------------------------------------------------------------------------
# utils
#---------------------------------------------------------------------------


def getHelperAndExp(expid, server=None):
    iotlab = IotlabHelper.IotlabHelper(server)
    exp = iotlab._makeExp(expid)
    expInfo = exp.getPersistentInfo()
    if (server == None and "args" in expInfo 
        and expInfo["args"].get("dev") != None):
        return getHelperAndExp(expid, expInfo["args"]["dev"])
    else: return iotlab, exp

def getProcessManager(exp):
    processManager = IotlabHelper.ProcessManager(False)
    processManager.setWindowTitle(exp.getPersistentInfo()["name"])
    return processManager



#---------------------------------------------------------------------------
# Main exp tools program
#---------------------------------------------------------------------------




print "(SSH FWD using last experiment id specified: exp %s)" % expId
#---------------------------------------------------------------------------
#"ssh-forward":
#---------------------------------------------------------------------------
#iotlab, exp = getHelperAndExp(expId)
processManager = getProcessManager(exp)
expInfo = exp.getPersistentInfo()

currentPort = [SshTunnelStartPort]
def getNewPort():
    result = currentPort[0]
    currentPort[0] += 1
    return result

forwardedTypeList = ForwardedTypeList[:]

forwardByType = {}
redirectList = []
nodes = []
for typeName, typeInfo in expInfo["nodeInfoByType"].iteritems():
    if typeName in forwardedTypeList:
        forwardList = [(node,getNewPort()) for node in typeInfo["nodes"]]
        redirectList.extend(
            ["-L %s:%s:%s" % (port, node, IotlabHelper.SerialTcpPort)
             for (node,port) in forwardList ])
        nodes.extend(typeInfo["nodes"])
        assert typeName not in forwardByType
        forwardByType[typeName] = forwardList

exp.writeFile("ssh-forward-port.json", IotlabHelper.toJson(forwardByType))

expServer = IotlabHelper.getExpUniqueServer(exp, nodes)

cmd = "echo FORWARDING PORTS"+str(redirectList)+"; sleep 600000"
sshRedirectPortStr = " ".join(redirectList)
sshSnifferTunnelCommand = "ssh -T %s@%s %s '%s'" % (
    iotlabHelper.userName, expServer, sshRedirectPortStr, cmd)
print "+", cmd
processManager.startSubProcessInTerm("ssh tunnels "+str(redirectList)+" to IoT-LAB", 
                                     sshSnifferTunnelCommand)



#----------------------------
#
#cmdPseudoTty(args)
#
#----------------------------

#forwardByType = IotlabHelper.fromJson(exp.readFile("ssh-forward-port.json"))
routerList = forwardByType.get("openwsn-sink")

routerList += forwardByType.get("openwsn")


for i,(node, port) in enumerate(routerList):
    socatCommand = ("sudo socat TCP4:localhost:%s " % port
                    + "pty,link=/dev/ttyUSB-pseudo-%s,raw" % i)
    print "++", socatCommand
    processManager.startSubProcessInTerm("Socat %s" % node, socatCommand)
    
    
#SocatFinal="sudo "
#for i,(node, port) in enumerate(routerList):
#    socatCommand = ("socat TCP4:localhost:%s " % port
#                    + "pty,link=/dev/ttyUSB-pseudo-%s,raw &&" % i)
#    print "++", socatCommand
#    SocatFinal=SocatFinal+socatCommand

#SocatFinal=SocatFinal+"echo done socat open"
#processManager.startSubProcessInTerm("Socat", SocatFinal)

	
print '1',ExperimentName, ' ',expId, ' ',time.strftime("%A %d %B %Y %H:%M:%S") 
#print '2',nodeList
print '2',routerList
print '3',flashedSinkList
#print '3',borderRouterNode
#print '4',borderRouterList
#print '5',expId
#print '6',SshTunnelStartPort
#print '7',routerList
#print '8',nodes

