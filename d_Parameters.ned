package inet.examples.d_Parameters;

/// Please populate this file with some code. ///
	// automatic configuration of all involved IP-nodes
import inet.networklayer.autorouting.FlatNetworkConfigurator;
	// measurement of throughput (PPP-Layer)
import inet.linklayer.ppp.ThruputMeter;
	// a routing device
import inet.nodes.inet.Router;
	// host with configurable applications
import inet.nodes.inet.StandardHost;
	// model description of rate-limited channel
import ned.DatarateChannel;

//
// d) parameter studies
// source and sink are connected via dataratechannels
// and throughput is measured 
//
// @Sudip Barua
//

network d_Parameters
{
	parameters:
    	int num_hosts;
    	double c_ber;
    	
    types:
    	
    	channel C1 extends DatarateChannel {
    		datarate = 1 Gbps;
    		delay = 0.1us;
    	}
    	
        channel C2 extends DatarateChannel {
            datarate = 1 Gbps;
            delay = 0.1us;
            ber = c_ber;
        }

    submodules:
        Source[num_hosts]: StandardHost {
            @display("p=70,111");
        }
        Router1: Router {
            @display("p=247,111");
        }
        Router2: Router {
            @display("p=300,111");
        }
        tm1: ThruputMeter {
            @display("p=320,130");
        }
        tm2: ThruputMeter {
            @display("p=342,130");
        }
        Sink: StandardHost {
            @display("p=448,111");
        }
        Configurator: FlatNetworkConfigurator {
            @display("p=247,41");
        }

    connections:
        for i=0..num_hosts-1{
        	Source[i].pppg$o++ --> C1 --> Router1.pppg$i++;
        }
        Router1.pppg$o++ --> C2 --> tm1.in;
        tm1.out --> C2 --> Router2.pppg$i++;
        Router2.pppg$o++ --> C1 --> tm2.in;
        tm2.out --> C1 --> Sink.pppg$i++;
        
        Sink.pppg$o++ --> C1 --> Router2.pppg$i++;
        Router2.pppg$o++ --> C2 --> Router1.pppg$i++;
        for i=0..num_hosts-1{
        	Router1.pppg$o++ --> C1 --> Source[i].pppg$i++;
        }
        
}