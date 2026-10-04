import { IndianRupee, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { BotReply } from "@/lib/types";

const inr = (v: number | string) => `₹${Number(v).toLocaleString("en-IN")}`;

function ago(unixSeconds: number): string {
  const hours = Math.max(1, Math.round((Date.now() / 1000 - unixSeconds) / 3600));
  return hours < 48 ? `${hours} hour${hours === 1 ? "" : "s"} ago` : `${Math.round(hours / 24)} days ago`;
}

export function PriceCard({ mandi, commodity }: { mandi: NonNullable<BotReply["details"]["mandi"]>; commodity: string }) {
  const rows = mandi.records.slice(0, 3);
  if (!rows.length) return null;
  const top = rows[0];

  return (
    <Card size="sm" className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <IndianRupee className="size-4 text-primary" />
          <span className="capitalize">{commodity}</span>
          <Badge variant={mandi.source === "live" ? "default" : "secondary"}>
            {mandi.source === "live" ? "Live" : mandi.source === "cached" ? "Saved" : "Sample"}
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
        {mandi.source === "cached" && mandi.fetched_at && (
          <Alert>
            <TriangleAlert />
            <AlertDescription>
              Live mandi data is unavailable right now. These prices were saved {ago(mandi.fetched_at)}.
            </AlertDescription>
          </Alert>
        )}
        {mandi.source === "sample" && (
          <Alert>
            <TriangleAlert />
            <AlertDescription>
              Live mandi data is unavailable right now, so these are sample prices for demonstration only.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
