"use client"

import { ArrowUpRight, ArrowDownRight } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useState, useEffect } from "react"
import mockData30d from "../data/mock-analytics-30d.json"

interface DailyHistory {
  date: string
  day_of_week: string
  viewers: number
  customers: number
  average_view_time: number
}

interface RevenueChartProps {
  dailyHistory: DailyHistory[]
  orgId?: string
}

const chartConfig = {
  viewers: {
    label: "Viewers",
    color: "hsl(var(--chart-1))",
  },
  customers: {
    label: "Customers",
    color: "hsl(var(--chart-2))",
  },
  average_view_time: {
    label: "Avg View Time",
    color: "hsl(var(--chart-3))",
  },
} satisfies ChartConfig

// Calculate date range based on selected time range
const getDateRange = (range: string) => {
  const today = new Date()
  today.setHours(23, 59, 59, 999) // End of today

  let startDate = new Date()

  if (range === "7d") {
    startDate.setDate(today.getDate() - 7)
  } else if (range === "30d") {
    startDate.setDate(today.getDate() - 30)
  } else {
    // For "all", use a large range (e.g., 365 days)
    startDate.setDate(today.getDate() - 365)
  }

  startDate.setHours(0, 0, 0, 0) // Start of day

  return {
    start: startDate.toISOString().split('T')[0], // YYYY-MM-DD format
    end: today.toISOString().split('T')[0]
  }
}

export default function RevenueChart({ dailyHistory: initialDailyHistory, orgId = "test" }: RevenueChartProps) {
  const [timeRange, setTimeRange] = useState("7d")
  const [dailyHistory, setDailyHistory] = useState<DailyHistory[]>(initialDailyHistory)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Track if this is the initial mount
  const [isInitialMount, setIsInitialMount] = useState(true)

  // Load mock data when time range changes (but not on initial mount)
  useEffect(() => {
    if (isInitialMount) {
      setIsInitialMount(false)
      return
    }

    const loadMockData = async () => {
      try {
        setIsLoading(true)
        setError(null)

        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 300))

        // Use 30-day mock data for 30d and all ranges
        if (timeRange === "30d" || timeRange === "all") {
          setDailyHistory(mockData30d.data.daily_history as DailyHistory[])
        } else {
          // For 7d, use the initial data
          setDailyHistory(initialDailyHistory)
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load mock data"
        setError(errorMessage)
        console.error("Error loading mock data:", err)
      } finally {
        setIsLoading(false)
      }
    }

    loadMockData()

    /* COMMENTED OUT - API CALL (use when backend is ready)
    const fetchAnalytics = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const { start, end } = getDateRange(timeRange)
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        const url = `${apiBaseUrl}/api/v1/analytics/?org_id=${orgId}&start_date=${start}&end_date=${end}`

        const response = await fetch(url, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
          mode: "cors",
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const data = await response.json()
        setDailyHistory(data.data.daily_history || [])
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load analytics"
        setError(errorMessage)
        console.error("Error fetching analytics:", err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchAnalytics()
    */
  }, [timeRange, orgId, initialDailyHistory])

  // Filter data based on selected time range (for display)
  const getFilteredData = () => {
    const days = timeRange === "7d" ? 7 : timeRange === "30d" ? 30 : dailyHistory.length
    return dailyHistory.slice(-days)
  }

  const filteredData = getFilteredData()

  // Transform data for the chart
  const chartData = filteredData.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric"
    }),
    viewers: item.viewers,
    customers: item.customers,
    average_view_time: item.average_view_time,
  }))

  // Calculate totals for the selected period
  const totals = filteredData.reduce(
    (acc, item) => ({
      viewers: acc.viewers + item.viewers,
      customers: acc.customers + item.customers,
      avgViewTime: acc.avgViewTime + item.average_view_time,
    }),
    { viewers: 0, customers: 0, avgViewTime: 0 }
  )

  const avgViewTime = filteredData.length > 0
    ? (totals.avgViewTime / filteredData.filter(d => d.viewers > 0).length || 0).toFixed(1)
    : 0

  return (
    <Card className="h-full">
      <CardHeader className="p-4">
        <div className="flex items-center justify-between">
          <CardTitle>Analytics Overview</CardTitle>
          <Select value={timeRange} onValueChange={setTimeRange} disabled={isLoading}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="all">All time</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {isLoading && (
          <p className="text-sm text-muted-foreground mt-2">Loading...</p>
        )}
        {error && (
          <p className="text-sm text-red-500 mt-2">Error: {error}</p>
        )}
        <CardDescription>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <p className="text-2xl font-semibold text-black dark:text-white">
                {totals.viewers}
              </p>
              <span className="text-xs text-muted-foreground">viewers</span>
            </div>
            <div className="flex items-center gap-2">
              <p className="text-2xl font-semibold text-black dark:text-white">
                {totals.customers}
              </p>
              <span className="text-xs text-muted-foreground">customers</span>
            </div>
            <div className="flex items-center gap-2">
              <p className="text-2xl font-semibold text-black dark:text-white">
                {avgViewTime}s
              </p>
              <span className="text-xs text-muted-foreground">avg view time</span>
            </div>
          </div>
        </CardDescription>
      </CardHeader>
      <CardContent className="h-[300px] px-4">
        <ResponsiveContainer width="100%" height="100%">
          <ChartContainer config={chartConfig}>
            <BarChart accessibilityLayer data={chartData}>
              <ChartLegend content={<ChartLegendContent />} />
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="date"
                tickLine={false}
                tickMargin={10}
                axisLine={false}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
              />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent indicator="dashed" />}
              />
              <Bar
                dataKey="viewers"
                barSize={20}
                fill="var(--chart-1)"
                radius={4}
              />
              <Bar
                dataKey="customers"
                barSize={20}
                fill="var(--chart-2)"
                radius={4}
              />
              <Bar
                dataKey="average_view_time"
                barSize={20}
                fill="var(--chart-3)"
                radius={4}
              />
            </BarChart>
          </ChartContainer>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}