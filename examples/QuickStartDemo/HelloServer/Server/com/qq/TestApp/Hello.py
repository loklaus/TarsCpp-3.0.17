from tars.core import tarscore;
from tars.__rpc import ServantProxy;


#proxy for client
class HelloProxy(ServantProxy):
    def test(self, context = ServantProxy.mapcls_context()):
        oos = tarscore.TarsOutputStream();

        rsp = self.tars_invoke(ServantProxy.TARSNORMAL, "test", oos.getBuffer(), context, None);

        ios = tarscore.TarsInputStream(rsp.sBuffer);
        ret = ios.read(tarscore.int32, 0, True);

        return (ret);

    def testHello(self, sReq, context = ServantProxy.mapcls_context()):
        oos = tarscore.TarsOutputStream();
        oos.write(tarscore.string, 1, sReq);

        rsp = self.tars_invoke(ServantProxy.TARSNORMAL, "testHello", oos.getBuffer(), context, None);

        ios = tarscore.TarsInputStream(rsp.sBuffer);
        ret = ios.read(tarscore.int32, 0, True);
        sRsp = ios.read(tarscore.string, 2, True);

        return (ret, sRsp);




