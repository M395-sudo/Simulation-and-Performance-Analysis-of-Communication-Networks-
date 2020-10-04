
// Network topology:
//
//
//    data
//   ^----v
//
//   n0   n1
//   |    |
//   *    * AP "HomeNet"
//
//
//
//   *    * AP "NeighbourNet"
//   |    |
//   n2   n3
//
//   v----^
//    data

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"
#include "ns3/flow-monitor-module.h" // for FlowMonitor

using namespace ns3;

#define SIMNAME "InterferenceSim"
NS_LOG_COMPONENT_DEFINE (SIMNAME);

int main (int argc, char *argv[])
{
  /* Parameters */
  const int homeDst = 0;
  const int neighborDst = 2;
  std::string homeRate = "30.1Mbps";
  std::string neighborRate = "1Mbps";
  double homeStart = 5.0;
  double homeStop = 10.0;
  // double homeStart = 1.0; // changing the transmission time frame
  // double homeStop = 5.0;
  double neighborStart = 6.0;
  double neighborStop = 10.0;
  const Time simStop = Seconds(10.0);


  /* Command line access to parameters */
  CommandLine cmd;
  cmd.AddValue ("homeRate", "data rate of stream [30Mbps]", homeRate);
  cmd.AddValue ("neighborRate", "data rate of stream [30Mbps]", neighborRate);
  cmd.AddValue ("homeStart", "start time of stream [1.0]", homeStart);
  cmd.AddValue ("homeStop", "stop time of stream [10.0]", homeStop);
  cmd.AddValue ("neighborStart", "start time of stream [1.0]", neighborStart);
  cmd.AddValue ("neighborStop", "stop time of stream [10.0]", neighborStop);
  cmd.Parse (argc,argv);


  /* Nodes */
  NodeContainer nodes[4]; // for ap <-> client, home <-> neighbour
  for (int i = 0; i < 4; i++)
    nodes[i].Create (1);


  /* Mobility model */
  MobilityHelper mobility;
  mobility.SetPositionAllocator ("ns3::GridPositionAllocator",
      "MinX", DoubleValue (0.0),
      "MinY", DoubleValue (0.0),
      "DeltaX", DoubleValue (5.0),
      "DeltaY", DoubleValue (50.0),
      // "DeltaY", DoubleValue (500.0), // increasing the distance
      "GridWidth", UintegerValue (2),
      "LayoutType", StringValue ("RowFirst"));
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  for (int i = 0; i < 4; i++)
    mobility.Install (nodes[i]);


  /* Channel + PHY */
  YansWifiChannelHelper channel = YansWifiChannelHelper::Default ();
  YansWifiPhyHelper phy = YansWifiPhyHelper::Default ();
  phy.SetPcapDataLinkType (YansWifiPhyHelper::DLT_IEEE802_11_RADIO);
  phy.SetChannel (channel.Create ());
  phy.Set ("ChannelNumber", UintegerValue(6));


  /* MAC */
  WifiHelper wifi = WifiHelper::Default ();
  wifi.SetRemoteStationManager ("ns3::IdealWifiManager");
  QosWifiMacHelper mac = QosWifiMacHelper::Default ();
  NetDeviceContainer devices[4];
  for (int i = 0; i < 4; i++) {
      switch (i) {
      case 0:
        mac.SetType ("ns3::StaWifiMac",
            "Ssid", SsidValue (Ssid ("HomeNet")));
        break;
      case 1:
        mac.SetType ("ns3::ApWifiMac",
            "Ssid", SsidValue (Ssid ("HomeNet")));
        break;
      case 2:
        mac.SetType ("ns3::StaWifiMac",
            "Ssid", SsidValue (Ssid ("NeighbourNet")));
        break;
      case 3:
        mac.SetType ("ns3::ApWifiMac",
            "Ssid", SsidValue (Ssid ("NeighbourNet")));
        break;
      default:
        NS_ASSERT(false);
        break;
      }
      devices[i] = wifi.Install (phy, mac, nodes[i]);
  }


  /* Internet stack */
  InternetStackHelper stack;
  Ipv4AddressHelper address;
  Ipv4InterfaceContainer interfaces[4];
  for (int i = 0; i < 4; i++) {
      stack.Install (nodes[i]);
      switch (i) {
      case 0:
        address.SetBase ("192.168.1.0", "255.255.255.0");
        break;
      case 2:
        address.SetBase ("192.168.2.0", "255.255.255.0");
        break;
      default:
        break;
      }
      interfaces[i] = address.Assign (devices[i]);
  }


  /* Applications */

  /* Ping to fill the ARP cache */
  // This is a workround for the lack of perfect ARP, see Bug 187
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=187
  V4PingHelper ping(Ipv4Address("192.168.99.99")); // dummy address
  ping.SetAttribute("StartTime", TimeValue (Seconds (0.1)));
  ping.SetAttribute("StopTime", TimeValue (Seconds (0.2)));

  /* CBR stream */
  uint16_t cbrPort = 1234;
  OnOffHelper onoff ("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny(), cbrPort)); // dummy address
  onoff.SetAttribute ("PacketSize", UintegerValue (2000));
  onoff.SetAttribute ("OnTime",  StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
  onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));

  /* Packet Sink */
  // accepts packets without answering with ICMP Unreachable
  PacketSinkHelper sink("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny(), cbrPort)); // dummy address

  for (uint32_t i = 0; i < 4; i++) {
      switch (i) {
      case 0:
        sink.Install(nodes[i]);
        break;
      case 1:
        ping.SetAttribute ("Remote", Ipv4AddressValue (interfaces[homeDst].GetAddress(0)));
        ping.Install (nodes[i]);

        onoff.SetAttribute ("Remote", AddressValue(InetSocketAddress (interfaces[homeDst].GetAddress(0), cbrPort)));
        onoff.SetAttribute ("DataRate", StringValue (homeRate));
        onoff.SetAttribute ("StartTime", TimeValue (Seconds(homeStart)));
        onoff.SetAttribute ("StopTime", TimeValue (Seconds(homeStop)));
        onoff.Install (nodes[i]);
        break;
      case 2:
        sink.Install(nodes[i]);
        break;
      case 3:
        ping.SetAttribute ("Remote", Ipv4AddressValue (interfaces[neighborDst].GetAddress(0)));
        ping.Install (nodes[i]);

        onoff.SetAttribute ("Remote", AddressValue(InetSocketAddress (interfaces[neighborDst].GetAddress(0), cbrPort)));
        onoff.SetAttribute ("DataRate", StringValue (neighborRate));
        onoff.SetAttribute ("StartTime", TimeValue (Seconds(neighborStart)));
        onoff.SetAttribute ("StopTime", TimeValue (Seconds(neighborStop)));
        onoff.Install (nodes[i]);
        break;
      default:
        NS_ASSERT(false);
        break;
      }
  }


  /* Logging and data collecting */
  FlowMonitorHelper flowmon;
  Ptr<FlowMonitor> monitor = flowmon.InstallAll();


  /* Simulation */
  Simulator::Stop (simStop);
  Simulator::Run ();


  /* Analysis / plot generation */
  monitor->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier> (flowmon.GetClassifier ());
  std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats ();
  for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin (); i != stats.end (); ++i) {
      Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow (i->first);
      double duration = (i->first == 1 ? (homeStop - homeStart) : (neighborStop - neighborStart));
      std::cout << "Flow " << (i->first == 1 ? "HomeNet" : "NeighbourNet")
          << " (" << t.sourceAddress << " -> " << t.destinationAddress << ")\n";
      std::cout << "  Tx Bytes:   " << i->second.txBytes << "\n";
      std::cout << "  Rx Bytes:   " << i->second.rxBytes << "\n";
      std::cout << "  Throughput: " << i->second.rxBytes * 8.0 / duration / 1024 / 1024  << " Mbps\n";
  }


  /* Cleanup */
  Simulator::Destroy ();

  return 0;
}
