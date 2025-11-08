"use client"

import { ArrowUpRight } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  XAxis,
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
import { billboardsChartData, getConversionRate } from "../data/billboard-data"

const chartConfig = {
  viewers: {
    label: "📺 노출 수",
    color: "var(--chart-1)",
  },
  customers: {
    label: "🛍️ 매장 방문",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig

export default function RevenueChart() {
  const conversionRate = getConversionRate()
  
  return (
    <Card className="h-full">
      <CardHeader className="p-4">
        <div className="flex items-center justify-between">
          <CardTitle>📈 7일 추이 분석</CardTitle>
          <Select defaultValue="week">
            <SelectTrigger className="w-[100px]">
              <SelectValue placeholder="기간" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">7일</SelectItem>
              <SelectItem value="month">30일</SelectItem>
              <SelectItem value="quarter">분기</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <CardDescription>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-semibold text-black dark:text-white">
              전환율: {conversionRate.toFixed(1)}%
            </p>
            <Badge
              variant="secondary"
              className="bg-opacity-20 rounded-xl bg-emerald-500 px-[5px] py-[2px] text-[10px] leading-none"
            >
              <div className="flex items-center gap-[2px] text-emerald-500">
                <ArrowUpRight size={12} />
                <p className="text-[8px]">+2%</p>
              </div>
            </Badge>
          </div>
        </CardDescription>
      </CardHeader>
      <CardContent className="h-[calc(100%_-_106px)] px-4">
        <ResponsiveContainer width="100%" height="100%">
          <ChartContainer config={chartConfig}>
            <BarChart accessibilityLayer data={billboardsChartData}>
              <ChartLegend content={<ChartLegendContent />} />
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="date"
                tickLine={false}
                tickMargin={10}
                axisLine={false}
                tickFormatter={(value) => {
                  return typeof value === 'string' ? value.slice(0, 3) : value
                }}
              />

              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent indicator="dashed" />}
              />
              <Bar
                dataKey="viewers"
                barSize={20}
                fill="var(--color-viewers)"
                radius={4}
              />
              <Bar
                dataKey="customers"
                barSize={20}
                fill="var(--color-customers)"
                radius={4}
              />
            </BarChart>
          </ChartContainer>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}