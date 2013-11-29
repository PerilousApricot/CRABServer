"""
 CRABPackage - automates/simplifies rpm building
"""
import os.path
import subprocess


DEFAULT_TARGETS = "CRABServer,CRABClient,TaskWorker"
# These repos come from git clone, so we need to speicify the repo and ref
DEFAULT_CMSDIST_REPO = "git@github.com:cms-sw/cmsdist.git"
DEFAULT_CMSDIST_REF = "comp"
DEFAULT_PKGTOOLS_REPO = "git@github.com:cms-sw/pkgtools.git"
DEFAULT_PKGTOOLS_REF = "V00-21-XX"

DEFAULT_CRABCLIENT = "git://github.com/dmwm/CRABClient.git?obj=master/%{realversion}&export=CRABClient-%{realversion}&output=/CRABClient-%{realversion}.tar.gz"
DEFAULT_WMCORE = "git://github.com/dmwm/WMCore.git?obj=master/%{wmcver}&export=WMCore-%{wmcver}&output=/WMCore-%{n}-%{wmcver}.tar.gz"
# crabclient spec and crabserver specs have different defaults
DEFAULT_CS_CRABSERVER = "git://github.com/dmwm/CRABServer.git?obj=master/%{realversion}&export=CRABServer-%{realversion}&output=/CRABServer-%{realversion}.tar.gz"
DEFAULT_CC_CRABSERVER = "git://github.com/dmwm/CRABServer.git?obj=master/%{crabserverver}&export=CRABServer-%{crabserverver}&output=/CRABServer-%{crabserverver}.tar.gz"


def package(targets, crabServerPath, crabClientPath, wmCorePath, pkgToolsRepo,
            pkgToolsRef, cmsdistRepo, cmsdistRef, workDir,
            arch='slc5_amd64_gcc461'):
    """
    Entry function from setup.py
        Need to do a few things here:
            0) make a directory to stash files
            1) Handle arguments, updating with defaults if needed
            2) collect pkgtools/cmsdist repos
            3) replace spec file stuff with overrides (if needed)
            4) run cmsbuild
    """
    try:
        if not os.path.exists(workDir):
            os.makedirs(workDir)

        # TODO I feel like I had a reason for doing this....
        targets = replaceIfNone(targets, DEFAULT_TARGETS)
        cmsdistRepo = replaceIfNone(cmsdistRepo, DEFAULT_CMSDIST_REPO)
        cmsdistRef = replaceIfNone(cmsdistRef, DEFAULT_CMSDIST_REF)
        pkgToolsRepo = replaceIfNone(pkgToolsRepo, DEFAULT_PKGTOOLS_REPO)
        pkgToolsRef = replaceIfNone(pkgToolsRef, DEFAULT_PKGTOOLS_REF)
        wmCorePath = replaceIfNone(wmCorePath, DEFAULT_WMCORE)
        crabServerPath_CS = replaceIfNone(crabServerPath, DEFAULT_CS_CRABSERVER)
        crabServerPath_CC = replaceIfNone(crabServerPath, DEFAULT_CC_CRABSERVER)
        crabClientPath = replaceIfNone(crabServerPath, DEFAULT_CRABCLIENT)
        # collect pkgtools/cmsdist repos
        pkgToolsCheckout, cmsdistCheckout = getRepos(workDir,
                                                     pkgToolsRepo, pkgToolsRef,
                                                     cmsdistRepo, cmsdistRef)

        # replace spec files with overrides
        overrideSpecs(targets, cmsdistCheckout, crabServerPath_CS,
                      crabServerPath_CC, crabClientPath, wmCorePath)

        # run the cmsbuild
        buildSpecs(targets, workDir, arch, pkgToolsCheckout, cmsdistCheckout)
    finally:
        pass

def buildSpecs(targets, workDir, arch, pkgToolsCheckout, cmsdistCheckout):
    targetMap = { "CRABServer" : "crabserver",
                  "CRABClient" : "crabclient",
                  "TaskWorker" : "crabtaskworker" }
    args = { 'targetList' : " ".join([targetMap[x] for x in targets.split(",")]),
             'pkgTools'   : pkgToolsCheckout,
             'cmsdist'    : cmsdistCheckout,
             'workDir'    : os.path.join(workDir, 'build'),
             'arch'       : arch }

    cmd = "%(pkgTools)s/cmsBuild -j 10 --work-dir %(workDir)s -c %(cmsdist)s build %(targetList)s "
    cmd += "--repo comp.pre --arch %(arch)"
    print "Executing %s" % (cmd % args)
    

def getRepos(workDir, pkgToolsRepo, pkgToolsRef, cmsdistRepo, cmsdistRef):
    """
    If the *repo values point to actual filesystem paths, just use them
    """
    reposToGet = [ ('pkgtools', pkgToolsRepo, pkgToolsRef),
                   ('cmsdist', cmsdistRepo, cmsdistRef) ]
    retval = []
    for repo in reposToGet:
        title = repo[0]
        path = repo[1]
        ref = repo[2]

        if os.path.exists(path):
            retval.append(os.path.abspath(path))
            continue

        targetPath = os.path.join(workDir, title)
        if os.path.exists(targetPath):
            forceGitResetToRef(targetPath, ref)
            retval.append(os.path.abspath(targetPath))
            continue

        # No other options
        checkoutFromGit(targetPath, path, ref)
        retval.append(os.path.abspath(targetPath))
        continue
    return retval

def forceGitResetToRef(targetPath, ref):
    """
    Forces the git repo @ targetPath to be at ref + fetch
    """
    output, retval = cmdHelper("git fetch --all", targetPath)
    assert not retval, output
    output, retval = cmdHelper("git reset --hard %s" % ref, targetPath)
    assert not retval, output
    output, retval = cmdHelper("git checkout -f %s" % ref, targetPath)
    assert not retval, output
    output, retval = cmdHelper("git clean -d -f -f -x", targetPath)
    assert not retval, output
    output, retval = cmdHelper("git clean -f -X", targetPath)
    assert not retval, output

def cmdHelper(args, cwd, checkCode=False):
    """
    Need this because commands doesn't let you pass in a working directory
    """
    args = "unset LD_LIBRARY_PATH ; %s" % args
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=cwd,
                         shell=True)
    output, _ = p.communicate()
    retval = p.returncode
    if checkCode and not retval:
        raise RuntimeError, "Failed to execute command \"%s\" at %s. Stdout:\n%s" %\
                                (args,cwd,output)
    return output, retval

def checkoutFromGit(targetPath, path, ref):
    if not os.path.exists(targetPath):
        os.makedirs(targetPath)
    output, retval = cmdHelper("git clone %s ." % path, targetPath)
    if not os.path.exists(os.path.join(targetPath, '.git')):
        raise RuntimeError, "Couldn't clone path %s:\n%s" % output
    cmdHelper("git checkout %s" % ref, targetPath)

def replaceIfNone(val, default):
    if val == None:
        return default
    else:
        return val

def overrideSpecs(targets, cmsdistCheckout, crabServerPath_CS,
                   crabServerPath_CC, crabClientPath, wmCorePath):
    targetMapping = {'CRABServer' : 'crabserver.spec',
                      'CRABClient' : 'crabclient.spec',
                      'TaskWorker' : 'crabtaskworker.spec'}
    specMapping = { DEFAULT_CRABCLIENT : crabClientPath,
                    DEFAULT_WMCORE : wmCorePath,
                    DEFAULT_CS_CRABSERVER : crabServerPath_CS,
                    DEFAULT_CC_CRABSERVER : crabServerPath_CC}
    for target in targets.split(','):
        specChanged = False
        targetSpec = targetMapping[target]
        specHandle = open(os.path.join(cmsdistCheckout, targetSpec), 'r')
        replacementSpec = []
        for line in specHandle.readlines():
            if not line.startswith('Source'):
                replacementSpec.append(line)
                continue
            # which spec are we?
            sourceNum = line.split()[0]
            sourceVal = " ".join(line.split()[1:])
            # we get a newline from the readlines, add that back
            if not sourceVal in specMapping:
                replacementSpec.append(line)
                continue
            # replace this spec
            newLine = " ".join([sourceNum, specMapping[sourceVal]]) + '\n'
            replacementSpec.append(newLine)
            specChanged = True

        if specChanged:
            if replacementSpec[-1].endswith("\n"):
                replacementSpec[-1] = replacementSpec[-1][:-1]
            replacementString = "".join(replacementSpec)
            specTarget = os.path.join(cmsdistCheckout, targetSpec)
            open(specTarget, 'w').write(replacementString)
