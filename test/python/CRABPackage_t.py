"""
tests for the packaging system
"""
import os
import shutil
import tempfile

from CRABQuality import withTemporaryDirectory
from CRABPackage import *
from nose.tools import *

def testReplaceIfNone():
    assert replaceIfNone(None, "test") == "test"
    assert replaceIfNone("nope", "test") == "nope"

def testCmdHelper():
    # there will be a trailing newline
    eq_(cmdHelper("pwd", "/"), ("/\n", 0))

class testQualitySuite:
    def setUp(self):
        self.workDir = tempfile.mkdtemp('crab3-testing')
    def tearDown(self):
        shutil.rmtree(self.workDir)
    def testForceGitResetToRef(self):
        workDir = self.workDir
        def examineRepo(target):
            # make sure repo looks like the original
            eq_(open("%s/README" % target,"r").read(), '1\n')
            eq_(sorted(os.listdir(target)), ['.git','README'])
        # Null reset
        self.makeDummyRepo(workDir)
        forceGitResetToRef(workDir, 'initial')
        examineRepo(workDir)

        # modified a file
        cmdHelper("echo 2 >> README", workDir)
        forceGitResetToRef(workDir, 'initial')
        examineRepo(workDir)

        # added a new file
        cmdHelper("echo 3 > TESTFILE", workDir)
        forceGitResetToRef(workDir, 'initial')
        examineRepo(workDir)

    def makeDummyRepo(self, workDir):
        if not os.path.exists(workDir):
            os.makedirs(workDir)
        cmdHelper("git init", workDir)
        cmdHelper("echo 1 > README", workDir)
        cmdHelper("git add README", workDir)
        cmdHelper("git commit -m 'initial'", workDir)
        cmdHelper("git tag initial", workDir)
        cmdHelper("echo 2 > SECOND", workDir)
        cmdHelper("echo 3 >> README", workDir)
        cmdHelper("git add README SECOND", workDir)
        cmdHelper("git commit -m 'tag2'", workDir)
        cmdHelper("git tag tag2", workDir)



    def testGetReposExists(self):
        # use an existent path
        eq_(getRepos(self.workDir, '/', None,'/etc',None),
                     ['/','/etc'] )
    def testGetReposPreviouslyCached(self):
        # use a previously cached path
        repo1 = "%s/pkgtools" % self.workDir
        repo2 = "%s/cmsdist" % self.workDir
        self.makeDummyRepo(repo1)
        self.makeDummyRepo(repo2)
        assert os.path.exists(repo1)
        assert os.path.exists(repo2)
        eq_(getRepos(self.workDir, 'git://test', 'initial',
                                   'git://noexist', 'tag2'),
            [repo1,repo2] )
        assert not os.path.exists("%s/SECOND" % repo1)
        assert os.path.exists("%s/SECOND" % repo2)

    def testGetReposFromGit(self):
        repo1 = "%s/pkgtools-base" % self.workDir
        repo2 = "%s/cmsdist-base" % self.workDir
        self.makeDummyRepo(repo1)
        self.makeDummyRepo(repo2)
        assert os.path.exists(repo1)
        assert os.path.exists(repo2)
        eq_(getRepos(self.workDir, 'file://%s' % repo1, 'initial',
                                   'file://%s' % repo2, 'tag2'),
            ["%s/pkgtools" % self.workDir,"%s/cmsdist" % self.workDir] )
        assert not os.path.exists("%s/pkgtools/SECOND" % self.workDir)
        assert os.path.exists("%s/cmsdist/SECOND" % self.workDir)

    def testOverrideSpecs(self):
        dummySpec="""### RPM cms crabserver 3.3.0.rc1
yadda
yadda
Source0: git://github.com/dmwm/WMCore.git?obj=master/%{wmcver}&export=WMCore-%{wmcver}&output=/WMCore-%{n}-%{wmcver}.tar.gz
Source1: git://github.com/dmwm/CRABServer.git?obj=master/%{realversion}&export=CRABServer-%{realversion}&output=/CRABServer-%{realversion}.tar.gz"""
        open('%s/crabserver.spec' % self.workDir, 'w').write(dummySpec)
        overrideSpecs('CRABServer', self.workDir, DEFAULT_CS_CRABSERVER,
                      DEFAULT_CC_CRABSERVER, DEFAULT_CRABCLIENT,
                      DEFAULT_WMCORE)
        eq_(dummySpec,open("%s/crabserver.spec" % self.workDir, 'r').read())
        overrideSpecs('CRABServer', self.workDir, "FAKEPATH",
                      DEFAULT_CC_CRABSERVER, DEFAULT_CRABCLIENT,
                      DEFAULT_WMCORE)
        newSpec = open("%s/crabserver.spec" % self.workDir, 'r').read()
        assert newSpec.find('FAKEPATH') != -1
