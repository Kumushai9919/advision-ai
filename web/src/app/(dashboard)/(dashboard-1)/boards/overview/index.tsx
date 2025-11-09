"use client"

import { useState, useEffect } from "react"
import RevenueChart from "./components/revenue-chart"
import Ads from "./components/ads"
import Stats from "./components/stats"

interface AnalyticsResponse {
  success: boolean
  org_id: string
  period: {
    start: string
    end: string
    days: number
  }
  data: {
    summary: {
      total_viewers: number
      difference_total_viewers_percentage: number
      total_new_viewers: number
      total_customers: number
      difference_total_customers_percentage: number
      average_view_time: number
      difference_average_view_time: number
    }
    daily_history: Array<{
      date: string
      day_of_week: string
      viewers: number
      customers: number
      average_view_time: number
    }>
    ranking: Array<{
      rank: number
      billboard_id: string
      name: string | null
      location: string | null
      views: number
      visit_by_view: number
      viewing_duration: number
    }>
  }
}

export default function Overview() {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const orgId = "test"
        const startDate = "2025-11-03"
        const endDate = "2025-11-09"

        // Use environment variable or fallback to localhost
        const apiBaseUrl = "https://advisionapi.solutionaix.com"
        const url = `${apiBaseUrl}/api/v1/analytics/?org_id=${orgId}&start_date=${startDate}&end_date=${endDate}`

        console.log("Fetching analytics from:", url)

        const response = await fetch(url, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
          cache: "no-store",
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => response.statusText)
          throw new Error(
            `HTTP ${response.status}: ${errorText || response.statusText}`
          )
        }

        const data: AnalyticsResponse = await response.json()
        setAnalyticsData(data)
        setError(null)
      } catch (err) {
        let errorMessage = "Failed to load analytics"

        if (err instanceof TypeError && err.message === "Failed to fetch") {
          errorMessage = "Cannot connect to server. Please ensure the backend server is running on http://localhost:8000"
        } else if (err instanceof Error) {
          errorMessage = err.message
        }

        setError(errorMessage)
        console.error("Error fetching analytics:", err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading analytics...</p>
        </div>
      </div>
    )
  }

  if (error || !analyticsData) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col items-center justify-center py-12 gap-4">
          <p className="text-red-500 font-semibold">Error: {error || "Failed to load analytics"}</p>
          {error?.includes("Cannot connect to server") && (
            <div className="text-sm text-muted-foreground max-w-md text-center">
              <p>Make sure the backend server is running:</p>
              <code className="block mt-2 p-2 bg-muted rounded">
                cd server/backend && python -m uvicorn src.main:app --reload --port 8000
              </code>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="grid grid-cols-6 gap-5 lg:grid-cols-12">
        <Stats analyticsData={analyticsData} />
        <div className="col-span-6">
          <RevenueChart dailyHistory={analyticsData.data.daily_history} orgId={analyticsData.org_id} />
        </div>
      </div>
      {/* <div className="grid auto-rows-auto grid-cols-3 gap-4 md:grid-cols-6 lg:grid-cols-9">
        <Stats analyticsData={analyticsData} />
      </div> */}
      <div className="w-full">
        <Ads ranking={analyticsData.data.ranking} />
      </div>
    </div>
  )
}
