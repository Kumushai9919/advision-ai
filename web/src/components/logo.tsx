export function Logo({
  className = "",
  width = 24,
  height = 24,
}: {
  className?: string
  width?: number
  height?: number
}) {
  return (
    <span className={`font-bold text-xl ${className}`}>
      AdVision
    </span>
  )
}
