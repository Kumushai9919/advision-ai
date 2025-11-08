import RevenueChart from "./components/revenue-chart"
import Ads from "./components/ads"
import Stats from "./components/stats"

export default function Overview() {
  return (
    <div className="space-y-6">

      <div className="grid auto-rows-auto grid-cols-3 gap-4 md:grid-cols-6 lg:grid-cols-9">
        <Stats />
      </div>
      <div className="w-full">
        <RevenueChart />
      </div>

      <div className="w-full">
        <Ads />
      </div>
    </div>
  )
}