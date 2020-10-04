
// Network topology:
//
//
//   n0   n1
//   |    |
//   *    *
//
//   *    *
//   |    |
//   n2   n3
//
// 3 20Mbps Streams from 0,1,2 to 3

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"
#include "ns3/flow-monitor-module.h" // for FlowMonitor

using namespace ns3;

#define SIMNAME "EdcaSim"
NS_LOG_COMPONENT_DEFINE (SIMNAME);


/* implement the trace sink callback here */
void QoSMarker (UserPriority up,Ptr <const Packet> pkt)
{
 pkt->AddPacketTag(QosTag(UP_VO));
}


int main (int argc, char *argv[])
{
  /* Parameters */
  uint32_t nWifi = 4;
  uint8_t src1 = 0;
  uint8_t src2 = 1;
  uint8_t src3 = 2;
  uint8_t dst = 3;
  const double cbr1Start = 1.000;
  const double cbr2Start = 1.010;
  const double cbr3Start = 1.011;
  const double cbrStop = 4;
  const Time simStop = Seconds(4);


  /* Nodes */
  NodeContainer nodes;
  nodes.Create (nWifi);


  /* Mobility model */
  MobilityHelper mobility;
  mobility.SetPositionAllocator ("ns3::GridPositionAllocator",
      "MinX", DoubleValue (0.0),
      "MinY", DoubleValue (0.0),
      "DeltaX", DoubleValue (5.0),
      "DeltaY", DoubleValue (5.0),
      "GridWidth", UintegerValue (2),
      "LayoutType", StringValue ("RowFirst"));
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobility.Install (nodes);


  /* Channel + PHY */
  YansWifiChannelHelper channel = YansWifiChannelHelper::Default ();
  YansWifiPhyHelper phy = YansWifiPhyHelper::Default ();
  phy.SetChannel (channel.Create ());


  /* MAC */
  WifiHelper wifi = WifiHelper::Default ();
  wifi.SetRemoteStationManager ("ns3::IdealWifiManager");
  QosWifiMacHelper mac = QosWifiMacHelper::Default ();
  Ssid ssid = Ssid ("ns-3-test");
  mac.SetType ("ns3::AdhocWifiMac", "Ssid", SsidValue (ssid));
  NetDeviceContainer staDevices = wifi.Install (phy, mac, nodes);


  /* Internet stack*/
  InternetStackHelper stack;
  stack.Install (nodes);
  Ipv4AddressHelper address;
  address.SetBase ("192.168.1.0", "255.255.255.0");
  Ipv4InterfaceContainer interfaces = address.Assign (staDevices);


  /* Applications */

  /* Ping to fill the ARP cache */
  // This is a workround for the lack of perfect ARP, see Bug 187
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=187
  V4PingHelper ping(interfaces.GetAddress(dst));
  ping.SetAttribute("StopTime", TimeValue (Seconds (0.2)));
  // The slightly different start times and data rates are a workaround
  // for Bug 388 and Bug 912
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=912
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=388
  ping.SetAttribute("StartTime", TimeValue (Seconds (0.1)));
  ping.Install (nodes.Get (src1));
  ping.SetAttribute("StartTime", TimeValue (Seconds (0.1001)));
  ping.Install (nodes.Get (src2));
  ping.SetAttribute("StartTime", TimeValue (Seconds (0.1011)));
  ping.Install (nodes.Get (src3));

  /* CBR data streams */
  uint16_t cbrPort = 12345;
  OnOffHelper onoff  ("ns3::UdpSocketFactory", InetSocketAddress (interfaces.GetAddress(dst), cbrPort));
  onoff.SetAttribute ("PacketSize", UintegerValue (2000));
  onoff.SetAttribute ("OnTime",  StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
  onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
  onoff.SetAttribute ("DataRate", StringValue ("20.0000Mbps"));
  onoff.SetAttribute ("StartTime", TimeValue (Seconds (cbr1Start)));
  onoff.Install (nodes.Get (src1));

  onoff.SetAttribute ("DataRate", StringValue ("20.00011Mbps"));
  onoff.SetAttribute ("StartTime", TimeValue (Seconds (cbr2Start)));
  onoff.Install (nodes.Get (src2));

  onoff.SetAttribute ("DataRate", StringValue ("20.00111Mbps"));
  onoff.SetAttribute ("StartTime", TimeValue (Seconds (cbr3Start)));
  onoff.Install (nodes.Get (src3));

  /* Packet Sink */
  // accepts packets without answering with ICMP Unreachable
  PacketSinkHelper sink("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny(), cbrPort));
  sink.Install(nodes.Get(dst));


  /* connect to the trace source here */
  Config::ConnectWithoutContext("/NodeList/2/ApplicationList/*/$ns3::OnOffApplication/Tx",MakeBoundCallback(&QoSMarker,UP_VO));

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
      double duration;
      if (t.sourceAddress == interfaces.GetAddress(src1))
        duration = cbrStop - cbr1Start;
      else if (t.sourceAddress == interfaces.GetAddress(src2))
        duration = cbrStop - cbr2Start;
      else if (t.sourceAddress == interfaces.GetAddress(src3))
        duration = cbrStop - cbr3Start;
      else
        continue;
      std::cout << "Flow " << i->first << " (" << t.sourceAddress << " -> " << t.destinationAddress << ")\n";
      std::cout << "  Tx Bytes:   " << i->second.txBytes << "\n";
      std::cout << "  Rx Bytes:   " << i->second.rxBytes << "\n";
      std::cout << "  Throughput: " << i->second.rxBytes * 8.0 / duration / 1024 / 1024 << " Mbps\n";
  }


  /* Cleanup */
  Simulator::Destroy ();

  return 0;
}
