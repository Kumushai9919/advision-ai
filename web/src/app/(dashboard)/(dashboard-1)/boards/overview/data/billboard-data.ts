// app/(dashboard)/dashboard-2/data/data.ts
// 광고판 효율성 추적 데이터 구조 및 Mock 데이터

import {
  IconTrendingUp,
  IconShoppingCart,
  IconEye,
  IconClock,
} from "@tabler/icons-react"

// ============================================
// 1️⃣ 타입 정의
// ============================================

export interface BillboardStats {
  label: string
  description: string
  stats: number
  type: "up" | "down"
  percentage: number
  chartData: Array<{ value: number }>
  strokeColor: string
  icon: React.ComponentType<any>
}

export interface DailyBillboardData {
  date: string
  day_of_week: string
  viewers: number
  customers: number
  average_view_time: number
  conversion_rate: number
}

export interface BillboardInfo {
  id: string
  name: string
  location: string
  status: "active" | "inactive" | "paused"
  total_viewers: number
  total_customers: number
  average_view_time: number
  conversion_rate: number
  estimated_revenue: number
  change_percentage: number
}

export interface RevenueData {
  date: string
  viewers: number
  customers: number
}

// ============================================
// 2️⃣ 데이터 생성 함수
// ============================================

// 7일간의 일별 광고판 데이터 생성
export function generateDailyData(): DailyBillboardData[] {
  const days = ["Friday", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
  const dates = ["2025-11-01", "2025-11-02", "2025-11-03", "2025-11-04", "2025-11-05", "2025-11-06", "2025-11-07"]

  return days.map((day_of_week, idx) => {
    const viewers = Math.floor(Math.random() * 150) + 100 // 100-250
    const customers = Math.floor(viewers * (Math.random() * 0.08 + 0.03)) // 3-11% 전환율
    const average_view_time = Math.floor(Math.random() * 50) + 80 // 80-130초

    return {
      date: dates[idx],
      day_of_week,
      viewers,
      customers,
      average_view_time,
      conversion_rate: (customers / viewers) * 100,
    }
  })
}

// Stats 카드용 데이터 생성 (3가지 핵심 메트릭)
export function generateStatsData(): BillboardStats[] {
  const dailyData = generateDailyData()

  // 총계 계산
  const totalViewers = dailyData.reduce((sum, d) => sum + d.viewers, 0)
  const totalCustomers = dailyData.reduce((sum, d) => sum + d.customers, 0)
  const avgViewTime = Math.round(
    dailyData.reduce((sum, d) => sum + d.average_view_time, 0) / dailyData.length
  )

  // 차트 데이터 생성 (작은 라인 차트용)
  const viewersChartData = dailyData.map(d => ({ value: d.viewers }))
  const customersChartData = dailyData.map(d => ({ value: d.customers }))
  const timeChartData = dailyData.map(d => ({ value: d.average_view_time }))

  return [
    {
      label: "📺 총 노출 수",
      description: "지난주 광고판 노출 총 수",
      stats: totalViewers,
      type: "up",
      percentage: 12, // 샘플: 전주 대비 +12%
      chartData: viewersChartData,
      strokeColor: "#3b82f6",
      icon: IconEye,
    },
    {
      label: "🛍️ 매장 방문",
      description: "광고 노출 후 실제 매장 방문 수",
      stats: totalCustomers,
      type: "up",
      percentage: 2,
      chartData: customersChartData,
      strokeColor: "#10b981",
      icon: IconShoppingCart,
    },
    {
      label: "⏱️ 평균 시청시간",
      description: "광고판 시청 평균 시간 (초)",
      stats: avgViewTime,
      type: "up",
      percentage: 8,
      chartData: timeChartData,
      strokeColor: "#f59e0b",
      icon: IconClock,
    },
  ]
}

// Revenue 차트용 데이터 (7일 추이)
export function generateRevenueChartData(): RevenueData[] {
  const days = ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"]
  const dailyData = generateDailyData()

  return dailyData.map((d, idx) => ({
    date: days[idx],
    viewers: d.viewers,
    customers: d.customers,
  }))
}

// ============================================
// 3️⃣ 광고판 목록 (Ads 컴포넌트용)
// ============================================

export const billboards: BillboardInfo[] = [
  {
    id: "billboard_gangnam",
    name: "🌟 쿠팡 광고판 (강남점)",
    location: "강남역 대형 전광판",
    status: "active",
    total_viewers: 122,
    total_customers: 10,
    average_view_time: 123,
    conversion_rate: 8.2,
    estimated_revenue: 1200000,
    change_percentage: 12,
  },
  {
    id: "billboard_youngsoo",
    name: "🌟 쿠팡 광고판 (영수점)",
    location: "영수역 버스정류장",
    status: "active",
    total_viewers: 157,
    total_customers: 8,
    average_view_time: 115,
    conversion_rate: 5.1,
    estimated_revenue: 960000,
    change_percentage: -3,
  },
  {
    id: "billboard_jamsil",
    name: "🌟 쿠팡 광고판 (잠실점)",
    location: "잠실역 대형 광고판",
    status: "active",
    total_viewers: 116,
    total_customers: 5,
    average_view_time: 108,
    conversion_rate: 4.3,
    estimated_revenue: 600000,
    change_percentage: 5,
  },
]

// ============================================
// 4️⃣ 최종 Export (기존 코드와 호환)
// ============================================

export const dashboard2Stats = generateStatsData()

export const billboardsChartData = generateRevenueChartData()

// 추가: 단일 광고판 상세 데이터 조회 함수
export function getBillboardDetail(billboardId: string): BillboardInfo | undefined {
  return billboards.find(b => b.id === billboardId)
}

export function getDailyBillboardData(): DailyBillboardData[] {
  return generateDailyData()
}

export function getConversionRate(): number {
  const dailyData = generateDailyData()
  const totalViewers = dailyData.reduce((sum, d) => sum + d.viewers, 0)
  const totalCustomers = dailyData.reduce((sum, d) => sum + d.customers, 0)
  return (totalCustomers / totalViewers) * 100
}