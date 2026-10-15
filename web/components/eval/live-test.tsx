"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Check, Download, Loader2, RotateCcw, Sparkles, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { explainSentence } from "@/lib/api";
import type { Explanation, LiveSample } from "@/lib/eval-types";
import { classMetrics, pct, toCsv } from "@/lib/metrics";
import { cn } from "@/lib/utils";
import { Bar } from "./bars";
import { ClassTable } from "./class-table";
import { ConfusionMatrix } from "./confusion-matrix";

const INTENTS = ["crop_disease", "market_price", "weather", "general"];
const NICE: Record<string, string> = { crop_disease: "Crop problem", market_price: "Price", weather: "Weather", general: "General" };
const STORAGE = "kisanmitra.live-eval.v1";
const SAMPLES = [
  "mera tamatar peela ho raha hai",
  "नाशिक में प्याज का भाव क्या है",
  "will it rain in Pune tomorrow",
  "उद्या पाऊस पडेल का",
  "my tomatoo leaves look yello",
  "hello",
  "weather",
  "the whole plant suddenly died",
];
const TYPE_STYLE: Record<string, string> = {
  crop: "bg-primary/20 text-primary-foreground dark:text-foreground ring-primary/50",
  symptom: "bg-amber-500/25 ring-amber-500/50",
  location: "bg-sky-500/25 ring-sky-500/50",
};

function Highlighted({ result }: { result: Explanation }) {
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const e of result.entities) {
    if (e.start < cursor) continue;
    parts.push(<span key={`t${cursor}`}>{result.text.slice(cursor, e.start)}</span>);
    parts.push(
      <mark key={e.start} title={`${e.type}: ${e.value} (${e.how})`} className={cn("rounded px-1 py-0.5 ring-1", TYPE_STYLE[e.type])}>
        {result.text.slice(e.start, e.end)}
        <sup className="ml-1 text-[10px] font-semibold uppercase opacity-70">{e.type}</sup>
      </mark>,
    );
    cursor = e.end;
  }
  parts.push(<span key="rest">{result.text.slice(cursor)}</span>);
  return <p className="text-xl leading-relaxed">{parts}</p>;
}

/**
 * The interactive demo: type any sentence, see what the NLP pipeline understands, then say whether it was right.
 * Every answer you mark updates a live accuracy / precision / recall / F1 table computed from YOUR examples.
 */
export function LiveTest() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<Explanation | null>(null);
  const [busy, setBusy] = useState(false);
  const [wrongPicker, setWrongPicker] = useState(false);
  const [samples, setSamples] = useState<LiveSample[]>([]);
  const [loaded, setLoaded] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (raw) setSamples(JSON.parse(raw));
    } catch {}
    setLoaded(true);
  }, []);
  useEffect(() => {
    if (!loaded) return;
    try {
      localStorage.setItem(STORAGE, JSON.stringify(samples));
    } catch {}
  }, [samples, loaded]);

  const live = useMemo(() => classMetrics(samples, INTENTS), [samples]);

  async function analyse(sentence: string) {
    const t = sentence.trim();
    if (!t) return;
    setBusy(true);
    setWrongPicker(false);
    try {
      setResult(await explainSentence(t));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not analyse that sentence");
    } finally {
      setBusy(false);
    }
  }

  function record(actual: string) {
    if (!result) return;
    setSamples((prev) => [
      ...prev,
      { id: Math.random().toString(36).slice(2, 9), text: result.text, predicted: result.intent.label, actual, confidence: result.intent.confidence, ts: Date.now() },
    ]);
    setResult(null);
    setText("");
    setWrongPicker(false);
    input.current?.focus();
  }

  function download() {
    const url = URL.createObjectURL(new Blob([toCsv(samples)], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "kisanmitra-live-evaluation.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const sorted = result ? Object.entries(result.intent.probabilities).sort((a, b) => b[1] - a[1]) : [];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Sparkles className="size-4 text-primary" /> Try any sentence</CardTitle>
          <CardDescription>Hindi, Marathi, English or Hindi in English letters. Then say if the answer is right.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void analyse(text); }}>
            <Input ref={input} value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a farmer's question…" aria-label="Sentence to analyse" className="h-10 text-base" autoFocus />
            <Button type="submit" disabled={busy || !text.trim()} className="h-10">
              {busy ? <Loader2 className="animate-spin" /> : "Analyse"}
            </Button>
          </form>
          <div className="flex flex-wrap gap-2">
            {SAMPLES.map((s) => (
              <button key={s} type="button" onClick={() => { setText(s); void analyse(s); }} className="rounded-full border px-3 py-1 text-xs transition-colors hover:bg-muted">
                {s}
              </button>
            ))}
          </div>

          {result && (
            <div className="flex flex-col gap-4 rounded-xl border bg-muted/30 p-4">
              <Highlighted result={result} />
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Badge variant="outline">Language: {result.language.name}</Badge>
                <Badge variant="outline">{result.milliseconds} ms</Badge>
                {result.entities.length === 0 && <Badge variant="secondary">no crop / symptom / place found</Badge>}
              </div>
              <div className="flex flex-col gap-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">How sure is the model? (intent probabilities)</p>
                {sorted.map(([label, p], i) => (
                  <Bar key={label} label={NICE[label] ?? label} value={p} tone={i === 0 ? "primary" : "muted"} />
                ))}
              </div>
              <div className="flex flex-col gap-2 border-t pt-3">
                <p className="text-sm font-medium">Prediction: <b>{NICE[result.intent.label]}</b>. Is it correct?</p>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => record(result.intent.label)}><Check /> Correct</Button>
                  <Button variant="outline" onClick={() => setWrongPicker((v) => !v)}><X /> Wrong</Button>
                </div>
                {wrongPicker && (
                  <div className="flex flex-wrap items-center gap-2" role="group" aria-label="What should it have been?">
                    <span className="text-sm text-muted-foreground">It should have been:</span>
                    {INTENTS.filter((i) => i !== result.intent.label).map((i) => (
                      <Button key={i} size="sm" variant="secondary" onClick={() => record(i)}>{NICE[i]}</Button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your live results</CardTitle>
          <CardDescription>Computed on the sentences you just marked. Nothing is pre-filled.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {samples.length === 0 ? (
            <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              Analyse a sentence and mark it correct or wrong. The accuracy, precision, recall and F1 appear here and update with every sentence.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg bg-muted/50 p-3"><div className="text-2xl font-semibold tabular-nums">{samples.length}</div><div className="text-xs text-muted-foreground">sentences</div></div>
                <div className="rounded-lg bg-muted/50 p-3"><div className="text-2xl font-semibold tabular-nums text-primary">{pct(live.accuracy)}</div><div className="text-xs text-muted-foreground">accuracy</div></div>
                <div className="rounded-lg bg-muted/50 p-3"><div className="text-2xl font-semibold tabular-nums">{pct(live.macroF1)}</div><div className="text-xs text-muted-foreground">macro F1</div></div>
              </div>
              <ClassTable rows={live.perClass} title="Intent" />
              <ConfusionMatrix labels={INTENTS} matrix={live.confusion} />
              <div className="max-h-40 overflow-y-auto rounded-lg border text-sm">
                {[...samples].reverse().map((s) => (
                  <div key={s.id} className="flex items-center gap-2 border-b px-3 py-1.5 last:border-b-0">
                    <span className={cn("size-2 shrink-0 rounded-full", s.actual === s.predicted ? "bg-primary" : "bg-destructive")} aria-label={s.actual === s.predicted ? "correct" : "wrong"} />
                    <span className="min-w-0 flex-1 truncate">{s.text}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">{NICE[s.predicted]}{s.actual !== s.predicted && ` → ${NICE[s.actual]}`}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={download}><Download /> Download CSV</Button>
                <Button variant="ghost" size="sm" onClick={() => setSamples((p) => p.slice(0, -1))}><RotateCcw /> Undo last</Button>
                <Button variant="ghost" size="sm" onClick={() => setSamples([])}><Trash2 /> Clear</Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
