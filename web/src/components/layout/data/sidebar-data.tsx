import { 
  IconChecklist, 
  IconLayoutDashboard, 
  IconSettings, 
  IconUsers,
} from "@tabler/icons-react"
import { AudioWaveform, GalleryVerticalEnd } from "lucide-react"
import { cn } from "@/lib/utils"
import { Logo } from "@/components/logo"
import { type SidebarData } from "../types"

export const sidebarData: SidebarData = {
  user: {
    name: "ausrobdev",
    email: "rob@shadcnblocks.com",
    avatar: "/avatars/ausrobdev-avatar.png",
  },
  teams: [
    {
      name: "Shadcnblocks - Admin Kit",
      logo: ({ className }: { className: string }) => (
        <Logo className={cn("invert dark:invert-0", className)} />
      ),
      plan: "Nextjs + shadcn/ui",
    },
    {
      name: "Acme Inc",
      logo: GalleryVerticalEnd,
      plan: "Enterprise",
    },
    {
      name: "Acme Corp.",
      logo: AudioWaveform,
      plan: "Startup",
    },
  ],
  navGroups: [
    {
      title: "General",
      items: [
        {
          title: "Dashboard",
          icon: IconLayoutDashboard,
          items: [
            {
              title: "Dashboard 1",
              url: "/",
            },
            {
              title: "Dashboard 2",
              url: "/dashboard-2",
            },
            {
              title: "Dashboard 3",
              url: "/dashboard-3",
            },
          ],
        }, 
      ],
    }, 
    {
      title: "Other",
      items: [
        // {
        //   title: "Settings",
        //   icon: IconSettings,
        //   items: [
        //     {
        //       title: "General",
        //       icon: IconTool,
        //       url: "/settings",
        //     } ,
        //     {
        //       title: "Plans",
        //       icon: IconChecklist,
        //       url: "/settings/plans",
        //     }, 
        //     {
        //       title: "Notifications",
        //       icon: IconNotification,
        //       url: "/settings/notifications",
        //     },
        //   ],
        // },
        {
          title: "Settings",
          url: "/settings",
          icon: IconSettings,
        },
      ],
    },
  ],
}
