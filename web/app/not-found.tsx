import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center p-6">
      <div className="flex max-w-sm flex-col items-center gap-4 text-center">
        <span className="text-5xl" aria-hidden>
          🌾
        </span>
        <h1 className="text-xl font-semibold">Page not found</h1>
        <Link href="/" className={buttonVariants()}>
          Back to KisanMitra
        </Link>
      </div>
    </main>
  );
}
