"use client";

import type { ComponentProps } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

type Props = Omit<ComponentProps<typeof Button>, "children"> & {
  label: string;
  children: React.ReactNode;
};

/** Icon-only button with a tooltip and an accessible name. */
export function IconButton({ label, children, ...props }: Props) {
  return (
    <Tooltip>
      <TooltipTrigger render={<Button variant="ghost" size="icon-sm" aria-label={label} {...props} />}>
        {children}
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
