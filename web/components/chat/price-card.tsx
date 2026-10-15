import { IndianRupee } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { BotReply } from "@/lib/types";

const inr = (v: number | string) => `₹${Number(v).toLocaleString("en-IN")}`;

function asOf(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

/** Usual price range when no live or saved prices exist. Clearly an estimate, never a market report. */
function EstimateCard({ estimate, commodity }: { estimate: NonNullable<NonNullable<BotReply["details"]["mandi"]>["estimate"]>; commodity: string }) {
  const span = Math.max(1, estimate.high - estimate.low);
  const position = Math.min(100, Math.max(0, ((estimate.typical - estimate.low) / span) * 100));
  return (
    <Card size="sm" className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <IndianRupee className="size-4 text-primary" />
          <span className="capitalize">{commodity}</span>
          <Badge variant="secondary">Estimate</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div>
          <div className="flex items-baseline gap-1 text-3xl font-semibold tabular-nums">
            <span>₹</span>
            <NumberTicker value={estimate.typical} />
            <span className="text-sm font-normal text-muted-foreground">/ quintal, usual level</span>
          </div>
        </div>
        <div>
          <div className="relative h-2 rounded-full bg-muted" role="img" aria-label={`Usual range ${estimate.low} to ${estimate.high} rupees per quintal`}>
            <div className="absolute inset-y-0 rounded-full bg-primary/30" style={{ left: 0, right: 0 }} />
            <div className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary" style={{ left: `${position}%` }} />
          </div>
          <div className="mt-1.5 flex justify-between text-xs text-muted-foreground tabular-nums">
            <span>{inr(estimate.low)}</span>
            <span>usual range</span>
            <span>{inr(estimate.high)}</span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">An estimate of the usual price at this time of year, not today&apos;s market rate. Ask at your nearest mandi for today&apos;s rate.</p>
      </CardContent>
    </Card>
  );
}

export function PriceCard({ mandi, commodity }: { mandi: NonNullable<BotReply["details"]["mandi"]>; commodity: string }) {
  const rows = mandi.records.slice(0, 3);
  if (!rows.length && mandi.estimate) return <EstimateCard estimate={mandi.estimate} commodity={commodity} />;
  if (!rows.length) return null;
  const top = rows[0];

  return (
    <Card size="sm" className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <IndianRupee className="size-4 text-primary" />
          <span className="capitalize">{commodity}</span>
          <Badge variant={mandi.source === "live" ? "default" : "secondary"}>
            {mandi.source === "live"
              ? "Live"
              : mandi.source === "cached" && mandi.fetched_at
                ? `As of ${asOf(mandi.fetched_at)}`
                : "Demo data"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div>
          <div className="flex items-baseline gap-1 text-3xl font-semibold tabular-nums">
            <span>₹</span>
            <NumberTicker value={Number(top.modal_price)} />
            <span className="text-sm font-normal text-muted-foreground">/ quintal</span>
          </div>
          <p className="text-xs text-muted-foreground">
            {top.market}, {top.district}
          </p>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Market</TableHead>
              <TableHead className="text-right">Min</TableHead>
              <TableHead className="text-right">Modal</TableHead>
              <TableHead className="text-right">Max</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r, i) => (
              <TableRow key={`${r.market}-${i}`}>
                <TableCell className="font-medium">{r.market}</TableCell>
                <TableCell className="text-right tabular-nums">{inr(r.min_price)}</TableCell>
                <TableCell className="text-right font-medium tabular-nums">{inr(r.modal_price)}</TableCell>
                <TableCell className="text-right tabular-nums">{inr(r.max_price)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
