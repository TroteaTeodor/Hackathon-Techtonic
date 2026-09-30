"use client";

import { Toaster as Sonner } from "sonner";

/** Short confirmations for actions, in the brand's navy; top-center so a thumb never covers them. */
export function Toaster() {
  return (
    <Sonner
      position="top-center"
      offset={16}
      mobileOffset={{ top: 76, left: 12, right: 12 }}
      gap={8}
      visibleToasts={3}
      toastOptions={{
        duration: 2800,
        classNames: {
          toast:
            "!rounded-2xl !border-0 !bg-navy-900 !text-white !shadow-[0_18px_40px_-16px_rgb(4_24_51/0.6)] !font-sans !px-4 !py-3",
          title: "!text-[14px] !font-semibold",
          description: "!text-[13px] !text-ice/75",
          icon: "!text-cyan-400",
          actionButton: "!bg-cyan-500 !text-navy-950 !font-semibold !rounded-lg",
        },
      }}
    />
  );
}
