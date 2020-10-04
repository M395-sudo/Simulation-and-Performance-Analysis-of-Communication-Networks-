
// Network topology:
//
//
//             AP
//   *    *    *
//   |    |    |
//   n0   n1   n2
//
//   v----^
//    data

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"

using namespace ns3;

#define SIMNAME "ApSim"
NS_LOG_COMPONENT_DEFINE (SIMNAME);

void PhyTxPacketTrace(Ptr<const Packet> pkt)
{
  WifiMacHeader hdr;

  pkt->PeekHeader(hdr);
  NS_LOG_DEBUG("Phy sent packet #" << pkt->GetUid() << " " << hdr.GetTypeString()
      << "\tToDs=" << hdr.IsToDs() << " FromDs=" << hdr.IsFromDs()
      << "\tAddr1=" << hdr.GetAddr1() << " Addr2=" << hdr.GetAddr2()
      << " Addr3=" << hdr.GetAddr3());
}

int main (int argc, char *argv[])
{
  /* Parameters */
  const int nClients = 2;
  const int src = 0;
  const int dst = nClients - 1;
  const Time pingStart = Seconds(1.0);
  const Time pingStop = Seconds(1.19);
  const Time pingInterval = Seconds(0.1);
  const Time simStop = Seconds(2.0);
  bool verbose = false;


  /* Command line access to parameters */
  CommandLine cmd;
  cmd.AddValue ("verbose", "lots of output [0]", verbose);
  cmd.Parse (argc,argv);


  /* Nodes */
  NodeContainer clientNodes;
  clientNodes.Create (nClients);
  NodeContainer apNode;
  apNode.Create (1);


  /* Mobility model */
  MobilityHelper mobility;
  mobility.SetPositionAllocator ("ns3::GridPositionAllocator",
      "MinX", DoubleValue (0.0),
      "MinY", DoubleValue (0.0),
      "DeltaX", DoubleValue (5.0),
      "DeltaY", DoubleValue (5.0),
      "GridWidth", UintegerValue (4),
      "LayoutType", StringValue ("RowFirst"));
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobility.Install (clientNodes);
  mobility.Install (apNode);


  /* Channel + PHY */
  YansWifiChannelHelper channel = YansWifiChannelHelper::Default ();
  YansWifiPhyHelper phy = YansWifiPhyHelper::Default ();
  phy.SetPcapDataLinkType (YansWifiPhyHelper::DLT_IEEE802_11_RADIO); // enables to see PHY information in .pcap
  phy.SetChannel (channel.Create ());


  /* MAC */

  WifiHelper wifi = WifiHelper::Default ();
  wifi.SetRemoteStationManager ("ns3::IdealWifiManager");
  NqosWifiMacHelper mac = NqosWifiMacHelper::Default ();
  Ssid ssid = Ssid ("ns-3-test");
  // mac.SetType ("ns3::StaWifiMac",
  mac.SetType ("ns3::AdhocWifiMac",
      "Ssid", SsidValue (ssid));

  // a) install MAC on Clients
  NetDeviceContainer staDevices = wifi.Install (phy, mac, clientNodes);

  // b) install MAC on AP
  mac.SetType ("ns3::ApWifiMac",
      "Ssid", SsidValue (ssid));
  NetDeviceContainer apDevice = wifi.Install (phy, mac, apNode);


  /* Internet stack */
  InternetStackHelper stack;
  stack.Install (apNode);
  stack.Install (clientNodes);
  Ipv4AddressHelper address;
  address.SetBase ("192.168.1.0", "255.255.255.0");
  Ipv4InterfaceContainer clientInterfaces = address.Assign (staDevices);
  address.Assign (apDevice);


  /* Applications */

  /* 1st Ping to fill the ARP cache */
  // This is a workround for the lack of perfect ARP, see Bug 187
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=187
  V4PingHelper ping(clientInterfaces.GetAddress(dst));
  ping.SetAttribute("StartTime", TimeValue (Seconds (0.1)));
  ping.SetAttribute("StopTime", TimeValue (Seconds (0.2)));
  ping.Install(clientNodes.Get(src));

  // 2nd Ping: src -> dst, 2 packets
  ping.SetAttribute("StartTime", TimeValue (pingStart));
  ping.SetAttribute("StopTime", TimeValue (pingStop));
  ping.SetAttribute("Verbose", BooleanValue (true));
  ping.SetAttribute("Interval", TimeValue (pingInterval));
  ping.Install(clientNodes.Get(src));


  /* Logging and data collecting */

  if (verbose) {
      LogComponentEnable(SIMNAME, LogLevel(LOG_LEVEL_INFO|LOG_PREFIX_TIME|LOG_PREFIX_NODE));
      Config::ConnectWithoutContext(
          "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyTxBegin",
          MakeCallback (&PhyTxPacketTrace));
  }

  /* write packet capture file as seen by AP */
  phy.EnablePcap (SIMNAME, apNode.Get (0)->GetId (), 0);


  /* Simulation */
  Simulator::Stop (simStop);
  Simulator::Run ();


  /* Analysis / plot generation */
  std::cout << "\nwritten capture of AP --> " << SIMNAME << "-" << apNode.Get (0)->GetId () << "-0.pcap\n" << std::endl;


  /* Cleanup */
  Simulator::Destroy ();

  return 0;
}
