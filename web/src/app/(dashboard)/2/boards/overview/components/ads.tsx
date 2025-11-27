// ============================================
// 3️⃣ Ads.tsx - 광고판 목록
// ============================================
// app/(dashboard)/dashboard-2/components/ads.tsx

"use client"

import * as React from "react"
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { ArrowUpDown, MoreHorizontal, TrendingUp, TrendingDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { BillboardInfo } from "../data/billboard-data"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"

interface RankingItem {
  rank: number
  billboard_id: string
  name: string | null
  location: string | null
  views: number
  visit_by_view: number
  viewing_duration: number
}

// ============================================
// 테이블 컬럼 정의
// ============================================

const columns: ColumnDef<BillboardInfo>[] = [
  // 광고판 이름
  {
    accessorKey: "name",
    header: "광고판",
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span className="font-medium">{row.getValue("name")}</span>
        <span className="text-xs text-gray-500">{row.original.location}</span>
      </div>
    ),
  },

  // 상태
  {
    accessorKey: "status",
    header: "상태",
    cell: ({ row }) => {
      const status = row.getValue("status") as string
      return (
        <Badge
          variant="outline"
          className={cn({
            "bg-green-50 text-green-700 border-green-200": status === "active",
            "bg-yellow-50 text-yellow-700 border-yellow-200": status === "paused",
            "bg-gray-50 text-gray-700 border-gray-200": status === "inactive",
          })}
        >
          {status === "active" && "활성"}
          {status === "paused" && "일시중지"}
          {status === "inactive" && "비활성"}
        </Badge>
      )
    },
  },

  // 노출 수
  {
    accessorKey: "total_viewers",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1"
      >
        📺 노출
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const viewers = row.getValue("total_viewers") as number
      return <div className="font-medium">{viewers.toLocaleString()}</div>
    },
  },

  // 전환 수
  {
    accessorKey: "total_customers",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1"
      >
        🛍️ 전환
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const customers = row.getValue("total_customers") as number
      return <div className="font-medium text-green-600">{customers.toLocaleString()}</div>
    },
  },

  // 전환율
  {
    accessorKey: "conversion_rate",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1"
      >
        전환율
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const rate = row.getValue("conversion_rate") as number
      return (
        <div className="font-bold text-blue-600">
          {rate.toFixed(1)}%
        </div>
      )
    },
  },

  // 변화율
  {
    accessorKey: "change_percentage",
    header: "변화율",
    cell: ({ row }) => {
      const change = row.getValue("change_percentage") as number
      const isPositive = change >= 0

      return (
        <div
          className={cn("flex items-center gap-1 font-medium", {
            "text-green-600": isPositive,
            "text-red-600": !isPositive,
          })}
        >
          {isPositive ? (
            <TrendingUp className="h-4 w-4" />
          ) : (
            <TrendingDown className="h-4 w-4" />
          )}
          {isPositive ? "+" : ""}{change}%
        </div>
      )
    },
  },

  // 추정 매출
  {
    accessorKey: "estimated_revenue",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1"
      >
        💰 매출
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const revenue = row.getValue("estimated_revenue") as number
      return (
        <div className="font-medium text-purple-600">
          ₩{(revenue / 1_000_000).toFixed(1)}M
        </div>
      )
    },
  },

  // 액션
  {
    id: "actions",
    enableHiding: false,
    cell: ({ row }) => {
      const billboard = row.original

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">메뉴 열기</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>작업</DropdownMenuLabel>
            <DropdownMenuItem
              onClick={() => navigator.clipboard.writeText(billboard.id)}
            >
              ID 복사
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>상세 보기</DropdownMenuItem>
            <DropdownMenuItem>분석 보기</DropdownMenuItem>
            <DropdownMenuItem className="text-red-600">삭제</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    },
  },
]

// ============================================
// Ads 컴포넌트
// ============================================

interface AdsProps {
  ranking: RankingItem[]
}

export default function Ads({ ranking }: AdsProps) {
  // Handle empty ranking array
  if (!ranking || ranking.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-xl">쿠팡 광고판</CardTitle>
          <CardDescription>
            광고판별 노출 및 전환 현황
          </CardDescription>
        </CardHeader>
        <CardContent className="h-[calc(100%_-_102px)]">
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">No billboard data available</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Map ranking data to BillboardInfo format
  const billboards: BillboardInfo[] = ranking.map((item) => {
    // Calculate customers from views and visit_by_view ratio
    // visit_by_view is unique visitors / total views, so unique visitors = views * visit_by_view
    const uniqueVisitors = Math.round(item.views * item.visit_by_view)
    // Estimate customers as a percentage of unique visitors (using a conversion rate)
    const estimatedCustomers = Math.round(uniqueVisitors * 0.1) // 10% conversion rate estimate

    // Convert viewing_duration from minutes to seconds for average_view_time
    const averageViewTimeSeconds = Math.round(item.viewing_duration * 60)

    // Calculate conversion rate (customers / viewers)
    const conversionRate = item.views > 0 ? (estimatedCustomers / item.views) * 100 : 0

    // Estimate revenue (views * some multiplier, e.g., 1000 won per view)
    const estimatedRevenue = item.views * 10000 // 10,000 won per view

    return {
      id: item.billboard_id,
      name: item.name || `Billboard ${item.billboard_id}`,
      location: item.location || "Unknown",
      status: "active" as const,
      total_viewers: item.views,
      total_customers: estimatedCustomers,
      average_view_time: averageViewTimeSeconds,
      conversion_rate: conversionRate,
      estimated_revenue: estimatedRevenue,
      change_percentage: 0, // Can be calculated if we have historical data
    }
  })

  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    []
  )
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = React.useState({})

  const table = useReactTable({
    data: billboards,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  })

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-xl">🌟 쿠팡 광고판</CardTitle>
        <CardDescription>
          광고판별 노출 및 전환 현황 (강남점, 영수점, 잠실점)
        </CardDescription>
      </CardHeader>

      <CardContent className="h-[calc(100%_-_102px)]">
        {/* 필터 & 페이지네이션 상단 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">
              선택됨: {Object.keys(rowSelection).length}개
            </span>
          </div>


        </div>

        {/* 테이블 */}
        <div className="rounded-md border overflow-auto">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    return (
                      <TableHead
                        key={header.id}
                        className="[&:has([role=checkbox])]:pl-3"
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                      </TableHead>
                    )
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    data-state={row.getIsSelected() && "selected"}
                    className="hover:bg-gray-50 dark:hover:bg-slate-900/50"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell
                        key={cell.id}
                        className="[&:has([role=checkbox])]:pl-3"
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center"
                  >
                    광고판이 없습니다.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* 페이지네이션 */}
        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-gray-500">
            총 {table.getFilteredRowModel().rows.length}개
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              이전
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              다음
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}