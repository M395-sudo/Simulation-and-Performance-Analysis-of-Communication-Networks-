
// Network topology:
//
//
//        movement
//   ------------------>
//   *        *
//   |        |
//   n1       n2
//
//   v--------^
//    data

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"
#include "app-data-collector.h"
#include "rate-data-collector.h"

using namespace ns3;

#define SIMNAME "RateControlSim"
NS_LOG_COMPONENT_DEFINE (SIMNAME);

int main (int argc, char *argv[])
{
  /* Parameters */
  const int nWifi = 2;
  const int src = 0;
  const int dst = nWifi - 1;
  const Time cbrStart = Seconds(1.0);
  const Time cbrStop = Seconds(24.0);
  const Time simStop = Seconds(24.0);
  bool vectorGraphics = false;


  /* Command line access to parameters */
  CommandLine cmd;
  cmd.AddValue ("vectorGraphics", "create vector graphics [false]", vectorGraphics);
  cmd.Parse (argc,argv);


  /* Nodes */
  NodeContainer nodes;
  nodes.Create (nWifi);


  /* Mobility model */

  MobilityHelper mobility;
  mobility.SetPositionAllocator ("ns3::GridPositionAllocator",
      "MinX", DoubleValue (0.0),
      "MinY", DoubleValue (0.0),
      "DeltaX", DoubleValue (125.0),
      "DeltaY", DoubleValue (0.0),
      "GridWidth", UintegerValue (2),
      "LayoutType", StringValue ("RowFirst"));

  mobility.SetMobilityModel ("ns3::ConstantVelocityMobilityModel");
  mobility.Install (nodes);

  // one of the nodes will be mobile
  Ptr <ConstantVelocityMobilityModel> movementSrc = nodes.Get(src)->GetObject<ConstantVelocityMobilityModel>();
  movementSrc->SetVelocity(Vector3D (10, 0, 0));


  /* Channel + PHY */
  YansWifiChannelHelper channel = YansWifiChannelHelper::Default ();
  YansWifiPhyHelper phy = YansWifiPhyHelper::Default ();
  phy.SetPcapDataLinkType (YansWifiPhyHelper::DLT_IEEE802_11_RADIO);
  phy.SetChannel (channel.Create ());


  /* MAC */
  WifiHelper wifi = WifiHelper::Default ();
  // wifi.SetRemoteStationManager ("ns3::AarfWifiManager");
  // wifi.SetRemoteStationManager ("ns3::MinstrelWifiManager");
  wifi.SetRemoteStationManager ("ns3::IdealWifiManager");
  QosWifiMacHelper mac = QosWifiMacHelper::Default ();
  Ssid ssid = Ssid ("ns-3-test");
  mac.SetType ("ns3::AdhocWifiMac",
      "Ssid", SsidValue (ssid));
  NetDeviceContainer devices = wifi.Install (phy, mac, nodes);


  /* Internet stack*/
  InternetStackHelper stack;
  stack.Install (nodes);
  Ipv4AddressHelper address;
  address.SetBase ("192.168.1.0", "255.255.255.0");
  Ipv4InterfaceContainer interfaces = address.Assign (devices);


  /* Applications */

  /* Ping to fill the ARP cache */
  // This is a workround for the lack of perfect ARP, see Bug 187
  // http://www.nsnam.org/bugzilla/show_bug.cgi?id=187
  V4PingHelper ping(interfaces.GetAddress(dst));
  ping.SetAttribute("StartTime", TimeValue (Seconds (0.1)));
  ping.SetAttribute("StopTime", TimeValue (Seconds (0.2)));
  ping.Install(nodes.Get(src));

  /* CBR stream */
  uint16_t cbrPort = 12345;
  OnOffHelper onoff ("ns3::UdpSocketFactory", InetSocketAddress (interfaces.GetAddress(dst), cbrPort));
  onoff.SetAttribute ("PacketSize", UintegerValue (2000));
  onoff.SetAttribute ("OnTime",  StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
  onoff.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
  onoff.SetAttribute ("DataRate", StringValue ("33.0000Mbps"));
  onoff.SetAttribute ("StartTime", TimeValue (cbrStart));
  onoff.SetAttribute ("StopTime", TimeValue (cbrStop));
  onoff.Install (nodes.Get (src));

  /* Packet Sink */
  // accepts packets without answering with ICMP Unreachable
  PacketSinkHelper sink("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny(), cbrPort));
  sink.Install(nodes.Get(dst));


  /* Logging and data collecting */
  AppDataCollector appCollector(src, dst, 1, 0, 0.1, SIMNAME);
  RateDataCollector rateCollector(src, dst, &devices, SIMNAME);


  /* Simulation */
  Simulator::Stop (simStop);
  Simulator::Run ();


  /* Analysis / plot generation */
  const std::string filenamePlot = std::string("plot_") + SIMNAME + std::string(".sh");
  std::ofstream filePlot(filenamePlot.c_str());
  filePlot << "gnuplot " << appCollector.CreatePlotFile(vectorGraphics) << std::endl;
  filePlot << "gnuplot " << rateCollector.CreatePlotFile(vectorGraphics) << std::endl;
  system(("chmod +x " + filenamePlot).c_str()); // make executable
  std::cout << "\nto plot the results, run './" << filenamePlot << "'" << std::endl;


  /* Cleanup */
  Simulator::Destroy ();

  return 0;
}
