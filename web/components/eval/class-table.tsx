import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { pct } from "@/lib/metrics";
import type { PerClass } from "@/lib/eval-types";
import { cn } from "@/lib/utils";

const NICE: Record<string, string> = { crop_disease: "Crop problem", market_price: "Price", weather: "Weather", general: "General" };

function Score({ v, none }: { v: number; none?: boolean }) {
  if (none) return <span className="text-muted-foreground">-</span>;
  return (
    <span className={cn("tabular-nums font-medium", v >= 0.9 ? "text-primary" : v >= 0.75 ? "text-amber-600 dark:text-amber-400" : "text-destructive")}>
      {pct(v)}
    </span>
  );
}

export function ClassTable({ rows, macro, weighted, title = "Class" }: {
  rows: PerClass[];
  macro?: { precision: number; recall: number; f1: number };
  weighted?: { precision: number; recall: number; f1: number };
  title?: string;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{title}</TableHead>
          <TableHead className="text-right">Precision</TableHead>
          <TableHead className="text-right">Recall</TableHead>
          <TableHead className="text-right">F1</TableHead>
          <TableHead className="text-right">Sentences</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((c) => (
          <TableRow key={c.label}>
            <TableCell className="font-medium">{NICE[c.label] ?? c.label}</TableCell>
            <TableCell className="text-right"><Score v={c.precision} none={c.support === 0 && c.precision === 0} /></TableCell>
            <TableCell className="text-right"><Score v={c.recall} none={c.support === 0} /></TableCell>
            <TableCell className="text-right"><Score v={c.f1} none={c.support === 0} /></TableCell>
            <TableCell className="text-right tabular-nums text-muted-foreground">{c.support}</TableCell>
          </TableRow>
        ))}
        {macro && (
          <TableRow className="bg-muted/40 font-medium">
            <TableCell>Macro average</TableCell>
            <TableCell className="text-right"><Score v={macro.precision} /></TableCell>
            <TableCell className="text-right"><Score v={macro.recall} /></TableCell>
            <TableCell className="text-right"><Score v={macro.f1} /></TableCell>
            <TableCell />
          </TableRow>
        )}
        {weighted && (
          <TableRow className="bg-muted/40 font-medium">
            <TableCell>Weighted average</TableCell>
            <TableCell className="text-right"><Score v={weighted.precision} /></TableCell>
            <TableCell className="text-right"><Score v={weighted.recall} /></TableCell>
            <TableCell className="text-right"><Score v={weighted.f1} /></TableCell>
            <TableCell />
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
