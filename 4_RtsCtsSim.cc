
// Network topology:
//
//
//   n0   n1   n2
//   |    |    |
//   *    *    *
//
//   v----^
//        ^----v
//      data
//
// based on examples/wifi-hidden-terminal.cc by Pavel Boyko <boyko@iitp.ru>

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"
#include "ns3/flow-monitor-module.h" // for FlowMonitor
#include "ns3/propagation-module.h" // for MatrixPropagationModel

using namespace ns3;

int g_numPhyRxDropDataPackets; // dropped DATA packets at receiver PHY
int g_numPhyRxDropRtsCtsPackets; // dropped RTS/CTS packets at receiver PHY
int g_numPhyRxDropBytes; // overall lost Bytes at receiver PHY


/* implement the trace sink callback here */
void PhyRxDrop(Ptr<const Packet> pkt)
{
	g_numPhyRxDropBytes += pkt->GetSize();
	WifiMacHeader hdr;
	pkt ->PeekHeader(hdr);
	if(hdr.IsData())
		g_numPhyRxDropDataPackets +=1;
	if(hdr.IsRts() || hdr.IsCts())
		g_numPhyRxDropRtsCtsPackets +=1;
}

/// Run single 10 seconds experiment with enabled or disabled RTS/CTS mechanism
void experiment (bool enableCtsRts)
{
  const int numNodes = 3;
  const int src1 = 0;
  const int src2 = 2;
  const int dst = 1;
  const double cbrStart = 1.0;
  const double cbrStop = 10.0;
  const Time simStop = Seconds(10.0);

  // 0. Enable or disable CTS/RTS
  UintegerValue packetSizeThreshold = (enableCtsRts ? UintegerValue (100) : UintegerValue (2200));
  Config::SetDefault ("ns3::WifiRemoteStationManager::RtsCtsThreshold", packetSizeThreshold);

  // 1. Create nodes
  NodeContainer nodes;
  nodes.Create (numNodes);

  // 2. Place nodes somehow, this is required by every wireless simulation
  for (int i = 0; i < numNodes; ++i)
    nodes.Get(i)->AggregateObject (CreateObject<ConstantPositionMobilityModel> ());

  // 3. Create propagation loss matrix
  Ptr<MatrixPropagationLossModel> lossModel = CreateObject<MatrixPropagationLossModel> ();
  lossModel->SetDefaultLoss (200); // set default loss to 200 dB (no link)
  lossModel->SetLoss (nodes.Get (src1)->GetObject<MobilityModel>(), nodes.Get (dst)->GetObject<MobilityModel>(), 50, true); // set symmetric loss 0 <-> 1 to 50 dB
  lossModel->SetLoss (nodes.Get (src2)->GetObject<MobilityModel>(), nodes.Get (dst)->GetObject<MobilityModel>(), 50, true); // set symmetric loss 2 <-> 1 to 50 dB

  // 4. Create & setup wifi channel
  Ptr<YansWifiChannel> channel = CreateObject <YansWifiChannel> ();
  channel->SetPropagationLossModel (lossModel);
  channel->SetPropagationDelayModel (CreateObject <ConstantSpeedPropagationDelayModel> ());

  // 5. Install wireless devices
  WifiHelper wifi;
  wifi.SetStandard (WIFI_PHY_STANDARD_80211a);
  wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
      "DataMode",StringValue ("OfdmRate54Mbps"),
      "ControlMode",StringValue ("OfdmRate6Mbps"));
  YansWifiPhyHelper phy = YansWifiPhyHelper::Default ();
  phy.SetChannel (channel);
  NqosWifiMacHelper mac = NqosWifiMacHelper::Default ();
  mac.SetType ("ns3::AdhocWifiMac");
  NetDeviceContainer devices = wifi.Install (phy, mac, nodes);

  // 6. Install TCP/IP stack & assign IP addresses
  InternetStackHelper internet;
  internet.Install (nodes);
  Ipv4AddressHelper ipv4;
  ipv4.SetBase ("10.0.0.0", "255.0.0.0");
  Ipv4InterfaceContainer interfaces = ipv4.Assign (devices);

  // 7.a) Install applications: two echo requests
  // This is a workround for the lack of perfect ARP, see Bug 187
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=187
  V4PingHelper ping (interfaces.GetAddress(dst));
  ping.SetAttribute("StopTime", TimeValue (Seconds (0.2)));
  ApplicationContainer pingApps;
  // The slightly different start times and data rates are a workaround
  // for Bug 388 and Bug 912
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=912
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=388
  ping.SetAttribute ("StartTime", TimeValue (Seconds (0.001)));
  pingApps.Add (ping.Install (nodes.Get (src1)));
  ping.SetAttribute ("StartTime", TimeValue (Seconds (0.006)));
  pingApps.Add (ping.Install (nodes.Get (src2)));

  // 7.b) Install applications: two CBR streams each saturating the channel
  uint16_t cbrPort = 12345;
  OnOffHelper onoff ("ns3::UdpSocketFactory", InetSocketAddress (interfaces.GetAddress(dst), cbrPort));
  onoff.SetAttribute ("PacketSize", UintegerValue (1000));
  onoff.SetAttribute ("OnTime",  StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
  onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));

  // flow 1:  src1 -> dst
  onoff.SetAttribute ("DataRate", StringValue ("3Mbps"));
  onoff.SetAttribute ("StartTime", TimeValue (Seconds (1.000)));
  onoff.Install (nodes.Get (src1));

  // flow 2:  src2 -> dst
  onoff.SetAttribute ("DataRate", StringValue ("3.0011Mbps"));
  onoff.SetAttribute ("StartTime", TimeValue (Seconds (1.001)));
  onoff.Install (nodes.Get (src2));

  // Packet Sink to receive flows 1 and 2
  // accepts packets without answering with ICMP Unreachable
  PacketSinkHelper sink("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny(), cbrPort));
  sink.Install(nodes.Get(dst));

  // 8. Install FlowMonitor on all nodes
  FlowMonitorHelper flowmon;
  Ptr<FlowMonitor> monitor = flowmon.InstallAll();


  /* connect to the trace source here */
  Config::ConnectWithoutContext("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/$ns3::YansWifiPhy/PhyRxDrop",MakeCallback (&PhyRxDrop));

  g_numPhyRxDropDataPackets = 0;
  g_numPhyRxDropRtsCtsPackets = 0;
  g_numPhyRxDropBytes = 0;

  // 9. Run simulation
  Simulator::Stop (simStop);
  Simulator::Run ();

  // 10. Print per flow statistics
  monitor->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier> (flowmon.GetClassifier ());
  std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats ();
  for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin (); i != stats.end (); ++i) {
      Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow (i->first);
      std::cout << "Flow " << i->first  << " (" << t.sourceAddress << " -> " << t.destinationAddress << ")\n";
      std::cout << "  Tx Bytes:   " << i->second.txBytes << "\n";
      std::cout << "  Rx Bytes:   " << i->second.rxBytes << "\n";
      std::cout << "  Throughput: " <<  i->second.rxBytes * 8.0 / (cbrStop - cbrStart) / 1024 / 1024 << " Mbps\n\n";
  }
  std::cout << "Data Packet Collisions: " << g_numPhyRxDropDataPackets << "\n";
  std::cout << "RTS/CTS Collisions: " << g_numPhyRxDropRtsCtsPackets << "\n";
  std::cout << "Lost MBytes: " << (double) g_numPhyRxDropBytes / 1024 / 1024 << "\n\n";

  // 11. Cleanup
  Simulator::Destroy ();
}

int main (int argc, char **argv)
{
  std::cout << "Hidden station experiment with RTS/CTS disabled:\n" << std::flush;
  experiment (false);
  std::cout << "------------------------------------------------\n";
  std::cout << "Hidden station experiment with RTS/CTS enabled:\n";
  experiment (true);

  return 0;
}
