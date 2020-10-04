package inet.examples.a_SimpleQueue;

	// automatic configuration of all involved IP-nodes
import inet.networklayer.autorouting.FlatNetworkConfigurator;
	// measurement of throughput (PPP-Layer)
import inet.linklayer.ppp.qosThroughputMeter;
	// a routing device
import inet.nodes.inet.Router;
	// host with configurable applications
import inet.nodes.inet.QosStandardHost;
	// model description of rate-limited channel
import ned.DatarateChannel;

//
// a) simple queue scenario
// source and sink are connected via dataratechannels
// and throughput is measured 
//
// @author Khai
//

network a_SimpleQueue
{
	parameters:
    	@display("bgb=507,186");

    types:
    	
    	channel Cinf extends DatarateChannel {}
    	
        channel C extends DatarateChannel {
            datarate = 8 Mbps;
            delay = 0.1us;
        }

    submodules:
        Source: QosStandardHost {
            @display("p=70,111");
        }
        Router: Router {
            @display("p=247,111");
        }
        tm1: qosThroughputMeter {
            @display("p=162,130");
        }
        tm2: qosThroughputMeter {
            @display("p=342,130");
        }
        Sink: QosStandardHost {
            @display("p=448,111");
        }
        Configurator: FlatNetworkConfigurator {
            @display("p=247,41");
        }

    connections:
        Source.pppg$o++ --> Cinf --> tm1.in;
        tm1.out --> Cinf --> Router.pppg$i++;
        Router.pppg$o++ --> Cinf --> Source.pppg$i++;
        Router.pppg$o++ --> C --> tm2.in;
        tm2.out --> Cinf --> Sink.pppg$i++;
        Sink.pppg$o++ --> Cinf --> Router.pppg$i++;
}