import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Adaptive sheet — slides up from the bottom on mobile, centered modal on
 * desktop. Built on Radix Dialog primitive (same as shadcn `<Dialog>`).
 *
 * Use this for the "preview → tap to expand" pattern:
 *   - Tap a chart tile on mobile → BottomSheet opens with the full chart
 *   - Same code on desktop → opens as a centered modal
 */
const BottomSheet = DialogPrimitive.Root;
const BottomSheetTrigger = DialogPrimitive.Trigger;
const BottomSheetPortal = DialogPrimitive.Portal;
const BottomSheetClose = DialogPrimitive.Close;

type OverlayRef = React.ElementRef<typeof DialogPrimitive.Overlay>;
type OverlayProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>;

const BottomSheetOverlay = React.forwardRef<OverlayRef, OverlayProps>(
  ({ className, ...props }, ref) => (
    <DialogPrimitive.Overlay
      ref={ref}
      className={cn(
        "fixed inset-0 z-50 bg-black/60 backdrop-blur-sm",
        "data-[state=open]:animate-in data-[state=open]:fade-in-0",
        "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
        className,
      )}
      {...props}
    />
  ),
);
BottomSheetOverlay.displayName = "BottomSheetOverlay";

type ContentRef = React.ElementRef<typeof DialogPrimitive.Content>;
type ContentProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>;

const BottomSheetContent = React.forwardRef<ContentRef, ContentProps>(
  ({ className, children, ...props }, ref) => (
    <BottomSheetPortal>
      <BottomSheetOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed z-50 bg-card text-foreground shadow-lg",
          "inset-x-0 bottom-0 max-h-[90vh] overflow-y-auto rounded-t-2xl border-t border-border",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=open]:slide-in-from-bottom data-[state=closed]:slide-out-to-bottom",
          "data-[state=open]:duration-200 data-[state=closed]:duration-150",
          "md:inset-x-auto md:bottom-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2",
          "md:max-h-[85vh] md:w-full md:max-w-2xl md:rounded-lg md:border",
          "md:data-[state=open]:slide-in-from-bottom-0 md:data-[state=closed]:slide-out-to-bottom-0",
          "md:data-[state=open]:zoom-in-95 md:data-[state=closed]:zoom-out-95",
          className,
        )}
        {...props}
      >
        <div className="mx-auto mt-2 h-1 w-12 rounded-full bg-muted md:hidden" aria-hidden />
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
          <X className="h-4 w-4" />
          <span className="sr-only">Fermer</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </BottomSheetPortal>
  ),
);
BottomSheetContent.displayName = "BottomSheetContent";

const BottomSheetHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col gap-1.5 border-b border-border p-4 text-left md:p-6", className)}
    {...props}
  />
);
BottomSheetHeader.displayName = "BottomSheetHeader";

type TitleRef = React.ElementRef<typeof DialogPrimitive.Title>;
type TitleProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>;

const BottomSheetTitle = React.forwardRef<TitleRef, TitleProps>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-base font-semibold tracking-tight md:text-lg", className)}
    {...props}
  />
));
BottomSheetTitle.displayName = "BottomSheetTitle";

type DescRef = React.ElementRef<typeof DialogPrimitive.Description>;
type DescProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>;

const BottomSheetDescription = React.forwardRef<DescRef, DescProps>(
  ({ className, ...props }, ref) => (
    <DialogPrimitive.Description
      ref={ref}
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  ),
);
BottomSheetDescription.displayName = "BottomSheetDescription";

const BottomSheetBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("p-4 md:p-6", className)} {...props} />
);
BottomSheetBody.displayName = "BottomSheetBody";

export {
  BottomSheet,
  BottomSheetTrigger,
  BottomSheetClose,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetDescription,
  BottomSheetBody,
};
