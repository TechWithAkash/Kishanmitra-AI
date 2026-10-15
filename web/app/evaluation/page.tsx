"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CircleHelp, Download, FlaskConical, Loader2, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { BlurFade } from "@/components/ui/blur-fade";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Bar } from "@/components/eval/bars";
import { ClassTable } from "@/components/eval/class-table";
import { ConfusionMatrix } from "@/components/eval/confusion-matrix";
import { LiveTest } from "@/components/eval/live-test";
import { getEvaluation } from "@/lib/api";
import type { EvaluationReport } from "@/lib/eval-types";
import { pct } from "@/lib/metrics";
import { cn } from "@/lib/utils";

const NICE: Record<string, string> = { crop_disease: "Crop problem", market_price: "Price", weather: "Weather", general: "General" };

function Stat({ title, value, unit = "%", hint, decimals = 1 }: { title: string; value: number; unit?: string; hint: string; decimals?: number }) {
  return (
    <Card size="sm">
      <CardContent className="flex flex-col gap-1">
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          {title}
          <Tooltip>
            <TooltipTrigger render={<button type="button" aria-label={`What is ${title}?`} className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring" />}>
              <CircleHelp className="size-3.5" />
            </TooltipTrigger>
            <TooltipContent className="max-w-64">{hint}</TooltipContent>
          </Tooltip>
        </div>
        <div className="text-3xl font-semibold tabular-nums sm:text-4xl">
          <NumberTicker value={value} decimalPlaces={decimals} />
          <span className="text-xl text-muted-foreground">{unit}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function Explain({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg bg-muted/50 p-3 text-sm leading-relaxed text-muted-foreground">{children}</p>;
}

function ErrorList({ rows }: { rows: { text: string; true: string; pred: string; confidence?: number; language?: string }[] }) {
  if (rows.length === 0) return <p className="text-sm text-muted-foreground">No mistakes on this test set.</p>;
  return (
    <ul className="divide-y rounded-lg border text-sm">
      {rows.map((r) => (
        <li key={r.text} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
          <span className="min-w-0 flex-1 text-base">{r.text}</span>
          <span className="flex items-center gap-1.5 text-xs">
            <Badge variant="outline">should be: {NICE[r.true] ?? r.true}</Badge>
            <Badge variant="destructive">said: {NICE[r.pred] ?? r.pred}</Badge>
            {r.confidence !== undefined && <span className="text-muted-foreground tabular-nums">{Math.round(r.confidence * 100)}% sure</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function EvaluationPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [cell, setCell] = useState<{ t: string; p: string } | null>(null);

  const load = useCallback(async (refresh = false) => {
    setRefreshing(true);
    setError(null);
    try {
      setReport(await getEvaluation(refresh));
      if (refresh) toast.success("Evaluation re-run");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the evaluation");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const intent = report?.intent;
  const shownErrors = intent && cell ? intent.errors.filter((e) => e.true === cell.t && e.pred === cell.p) : intent?.errors ?? [];

  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-20 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <Link href="/" className={buttonVariants({ variant: "ghost", size: "sm" })}><ArrowLeft /> KisanMitra</Link>
          <h1 className="flex items-center gap-2 text-lg font-semibold"><FlaskConical className="size-5 text-primary" /> Model performance</h1>
          <div className="ml-auto flex items-center gap-2">
            <a href="/api/evaluation/report.md" download className={buttonVariants({ variant: "outline", size: "sm" })}><Download /> Report</a>
            <Button variant="outline" size="sm" onClick={() => void load(true)} disabled={refreshing}>
              {refreshing ? <Loader2 className="animate-spin" /> : <RefreshCw />} Re-run
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6">
        {error && (
          <Alert variant="destructive">
            <TriangleAlert />
            <AlertTitle>Could not load the numbers</AlertTitle>
            <AlertDescription>{error}. Is the backend running?</AlertDescription>
          </Alert>
        )}

        {!report && !error && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-24" />)}</div>
        )}

        {report && intent && (
          <>
            <BlurFade>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <Stat title="Intent accuracy" value={intent.accuracy * 100} hint="Out of all test sentences, how many did the model understand correctly (crop problem / price / weather / general)." />
                <Stat title="Intent macro-F1" value={intent.macro.f1 * 100} hint="F1 mixes precision and recall into one score, averaged over the 4 intents so a small class counts as much as a big one." />
                <Stat title="Language ID accuracy" value={report.langid.accuracy * 100} hint="How often the app correctly detected the language and script (Hindi, romanized Hindi, Marathi, English, Tamil, ...)." />
                <Stat title="Entity F1" value={report.entities.micro.f1 * 100} hint="How well it finds the crop, the symptom and the place inside a sentence. Optimistic: see the 'Data & limits' tab." />
                <Stat title="Speed per sentence" value={report.latency.stages.find((s) => s.stage === "Total")?.median_ms ?? 0} unit=" ms" decimals={2} hint="Median time to detect language, intent and entities for one sentence on one CPU thread." />
              </div>
              <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                <ShieldCheck className="size-4 text-primary" />
                Measured on <b className="text-foreground">{report.dataset.test_size} test sentences the model never saw</b> ({report.dataset.overlap_with_training} shared with the {report.dataset.train_size} training sentences).
              </p>
            </BlurFade>

            <Tabs defaultValue="intent">
              <TabsList className="h-auto flex-wrap justify-start">
                <TabsTrigger value="intent">Intent</TabsTrigger>
                <TabsTrigger value="models">Model comparison</TabsTrigger>
                <TabsTrigger value="language">Language ID</TabsTrigger>
                <TabsTrigger value="entities">Entities</TabsTrigger>
                <TabsTrigger value="speed">Speed</TabsTrigger>
                <TabsTrigger value="live">Try it live</TabsTrigger>
                <TabsTrigger value="data">Data &amp; limits</TabsTrigger>
              </TabsList>

              {/* ---------------- intent */}
              <TabsContent value="intent" className="mt-4 grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Precision, recall and F1 per intent</CardTitle>
                    <CardDescription>{intent.n} unseen sentences · Cohen&apos;s kappa {intent.kappa}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <ClassTable rows={intent.per_class} macro={intent.macro} weighted={intent.weighted} title="Intent" />
                    <Explain>
                      <b>Precision</b>: when the model says &ldquo;price&rdquo;, how often is it really a price question? <b>Recall</b>: of all real price questions, how many did it find? <b>F1</b>: one score that is low if either one is low.
                    </Explain>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Confusion matrix</CardTitle>
                    <CardDescription>Where exactly does it go wrong? Click a red cell.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ConfusionMatrix labels={intent.labels} matrix={intent.confusion} selected={cell} onSelect={(t, p) => setCell((c) => (c?.t === t && c?.p === p ? null : t !== p ? { t, p } : null))} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Accuracy by language</CardTitle>
                    <CardDescription>The same model, on each language of the test set</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2.5">
                    {intent.by_language.map((g) => <Bar key={g.group} label={g.group} value={g.accuracy} note={`${g.n} sentences`} />)}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Is the model honest about being unsure?</CardTitle>
                    <CardDescription>Average confidence: {pct(intent.mean_confidence_correct)} when right, {intent.mean_confidence_wrong !== null ? pct(intent.mean_confidence_wrong) : "n/a"} when wrong</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2.5">
                    {intent.calibration.filter((c) => c.n > 0).map((c) => (
                      <Bar key={c.range} label={`says ${c.range} sure`} value={c.accuracy ?? 0} note={`${c.n} sentences`} tone={(c.accuracy ?? 0) >= 0.9 ? "primary" : "amber"} />
                    ))}
                    <Explain>A good model is right more often when it is more confident. Low-confidence answers could be sent to the farmer as &ldquo;please rephrase&rdquo;.</Explain>
                  </CardContent>
                </Card>

                <Card className="lg:col-span-2">
                  <CardHeader>
                    <CardTitle>Mistakes ({shownErrors.length}{cell ? `: ${NICE[cell.t]} read as ${NICE[cell.p]}` : ""})</CardTitle>
                    <CardDescription>Reading the errors tells us what to improve next</CardDescription>
                  </CardHeader>
                  <CardContent><ErrorList rows={shownErrors} /></CardContent>
                </Card>
              </TabsContent>

              {/* ---------------- models */}
              <TabsContent value="models" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Six classifiers compared</CardTitle>
                    <CardDescription>The same 140 training sentences, the same {intent.n} test sentences</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Model</TableHead>
                          <TableHead className="text-right">5-fold CV macro-F1 (training data)</TableHead>
                          <TableHead className="text-right">Test accuracy</TableHead>
                          <TableHead className="text-right">Test macro-F1</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {[...report.models].sort((a, b) => b.cv_macro_f1_mean - a.cv_macro_f1_mean).map((m) => (
                          <TableRow key={m.model} className={cn(m.used_in_app && "bg-primary/10")}>
                            <TableCell className="font-medium">{m.model.replace(" (used in the app)", "")} {m.used_in_app && <Badge className="ml-1">used in the app</Badge>}</TableCell>
                            <TableCell className="text-right tabular-nums">{pct(m.cv_macro_f1_mean)} <span className="text-muted-foreground">± {pct(m.cv_macro_f1_std)}</span></TableCell>
                            <TableCell className="text-right tabular-nums">{pct(m.test_accuracy)}</TableCell>
                            <TableCell className="text-right tabular-nums">{pct(m.test_macro_f1)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    <div className="flex flex-col gap-2.5">
                      {[...report.models].sort((a, b) => b.test_macro_f1 - a.test_macro_f1).map((m) => (
                        <Bar key={m.model} label={m.model.replace(" (used in the app)", "")} value={m.test_macro_f1} tone={m.used_in_app ? "primary" : "muted"} />
                      ))}
                    </div>
                    <Explain>
                      <b>How the model was chosen:</b> by <b>cross-validation on the training data</b> (the training sentences are split in 5; each part is held out once). The test set is only used to <i>report</i> the result: choosing the best model by its test score would be cheating, because the test score would no longer be an honest estimate. The top few models are within one standard deviation of each other, so we keep the simplest one. The baseline that always answers &ldquo;crop problem&rdquo; scores only about 13%: that is what &ldquo;learning nothing&rdquo; looks like.
                    </Explain>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* ---------------- language id */}
              <TabsContent value="language" className="mt-4 grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Language identification</CardTitle>
                    <CardDescription>{report.langid.n} sentences, {report.langid.labels.length} language/script classes. Romanized Hindi counts as its own class.</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2.5">
                    {report.langid.by_language.map((g) => <Bar key={g.group} label={g.group} value={g.accuracy} note={`${g.n} sentences`} />)}
                    <Explain>It reads the script first (Devanagari, Tamil, Telugu, ...), then uses common words to separate Hindi from Marathi and romanized Hindi from English. Standard tools mislabel romanized Hindi.</Explain>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Per-language precision, recall, F1</CardTitle></CardHeader>
                  <CardContent><ClassTable rows={report.langid.per_class} macro={report.langid.macro} title="Language" /></CardContent>
                </Card>
                <Card className="lg:col-span-2">
                  <CardHeader><CardTitle>Confusion matrix ({report.langid.labels.length}×{report.langid.labels.length})</CardTitle></CardHeader>
                  <CardContent><ConfusionMatrix labels={report.langid.labels} matrix={report.langid.confusion} /></CardContent>
                </Card>
                <Card className="lg:col-span-2">
                  <CardHeader><CardTitle>Mistakes ({report.langid.errors.length})</CardTitle></CardHeader>
                  <CardContent>
                    {report.langid.errors.length === 0 ? <p className="text-sm text-muted-foreground">None.</p> : (
                      <ul className="divide-y rounded-lg border text-sm">
                        {report.langid.errors.map((e) => (
                          <li key={e.text} className="flex flex-wrap items-center gap-2 px-3 py-2"><span className="flex-1 text-base">{e.text}</span><Badge variant="outline">is: {e.true}</Badge><Badge variant="destructive">said: {e.pred}</Badge></li>
                        ))}
                      </ul>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* ---------------- entities */}
              <TabsContent value="entities" className="mt-4 grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Entity extraction</CardTitle>
                    <CardDescription>Finding the crop, the symptom and the place in a sentence · {report.entities.n} sentences</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <Table>
                      <TableHeader>
                        <TableRow><TableHead>Entity</TableHead><TableHead className="text-right">Precision</TableHead><TableHead className="text-right">Recall</TableHead><TableHead className="text-right">F1</TableHead><TableHead className="text-right">Found / in text</TableHead></TableRow>
                      </TableHeader>
                      <TableBody>
                        {report.entities.per_slot.map((s) => (
                          <TableRow key={s.slot}>
                            <TableCell className="font-medium capitalize">{s.slot}</TableCell>
                            <TableCell className="text-right tabular-nums">{pct(s.precision)}</TableCell>
                            <TableCell className="text-right tabular-nums">{pct(s.recall)}</TableCell>
                            <TableCell className="text-right tabular-nums">{pct(s.f1)}</TableCell>
                            <TableCell className="text-right tabular-nums text-muted-foreground">{s.tp} / {s.support}</TableCell>
                          </TableRow>
                        ))}
                        <TableRow className="bg-muted/40 font-medium">
                          <TableCell>Overall (micro)</TableCell>
                          <TableCell className="text-right tabular-nums">{pct(report.entities.micro.precision)}</TableCell>
                          <TableCell className="text-right tabular-nums">{pct(report.entities.micro.recall)}</TableCell>
                          <TableCell className="text-right tabular-nums">{pct(report.entities.micro.f1)}</TableCell>
                          <TableCell />
                        </TableRow>
                      </TableBody>
                    </Table>
                    <Bar label="Every entity in a sentence exactly right" value={report.entities.strict_accuracy} />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Read this number carefully</CardTitle></CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <Alert>
                      <TriangleAlert />
                      <AlertTitle>Optimistic result</AlertTitle>
                      <AlertDescription>The keyword lists (8 crops, about 40 cities, 6 symptom groups) and the test sentences were written by the same person, so the words match. On a farmer&apos;s sentence with a crop or village we do not list, recall would fall. The fair way to improve this is a bigger, independently collected test set.</AlertDescription>
                    </Alert>
                    <Explain>Spelling mistakes such as &ldquo;tomatoo&rdquo; or &ldquo;yello&rdquo; are corrected with an edit-distance rule, and the 🧪 &ldquo;Try it live&rdquo; tab shows when that happened.</Explain>
                  </CardContent>
                </Card>
                <Card className="lg:col-span-2">
                  <CardHeader><CardTitle>Mistakes ({report.entities.errors.length})</CardTitle></CardHeader>
                  <CardContent>
                    {report.entities.errors.length === 0 ? <p className="text-sm text-muted-foreground">None.</p> : (
                      <ul className="divide-y rounded-lg border text-sm">
                        {report.entities.errors.map((e) => (
                          <li key={`${e.text}-${e.slot}`} className="flex flex-wrap items-center gap-2 px-3 py-2">
                            <span className="min-w-0 flex-1 text-base">{e.text}</span>
                            <Badge variant="outline">{e.slot}</Badge><Badge variant="secondary">{e.kind}</Badge>
                            <span className="text-xs text-muted-foreground">expected {e.gold ?? "nothing"}, got {e.pred ?? "nothing"}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* ---------------- speed */}
              <TabsContent value="speed" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle>How fast is each step?</CardTitle>
                    <CardDescription>{report.latency.samples} measurements, one sentence at a time, one CPU thread</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    {report.latency.stages.map((s) => (
                      <div key={s.stage} className="grid gap-1">
                        <Bar label={`${s.stage} (median)`} value={Math.min(1, s.median_ms / Math.max(...report.latency.stages.map((x) => x.p95_ms)))} suffix={`${s.median_ms} ms`} tone="primary" />
                        <Bar label={`${s.stage} (slowest 5%)`} value={Math.min(1, s.p95_ms / Math.max(...report.latency.stages.map((x) => x.p95_ms)))} suffix={`${s.p95_ms} ms`} tone="amber" />
                      </div>
                    ))}
                    <Explain>Understanding a sentence takes a fraction of a millisecond. In the real app, the time a farmer waits is spent on the outside services (weather, mandi prices, translation, speech), not on the NLP itself.</Explain>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* ---------------- live */}
              <TabsContent value="live" className="mt-4"><LiveTest /></TabsContent>

              {/* ---------------- data */}
              <TabsContent value="data" className="mt-4 grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader><CardTitle>The data</CardTitle><CardDescription>Training: {report.dataset.train_size} sentences. Test: {report.dataset.test_size} sentences.</CardDescription></CardHeader>
                  <CardContent className="flex flex-col gap-2.5">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Training sentences per intent</p>
                    {Object.entries(report.dataset.train_by_intent).map(([k, v]) => <Bar key={k} label={NICE[k] ?? k} value={v / report.dataset.train_size} suffix={`${v}`} tone="sky" />)}
                    <p className="mt-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Test sentences per intent</p>
                    {Object.entries(report.dataset.test_by_intent).map(([k, v]) => <Bar key={k} label={NICE[k] ?? k} value={v / report.dataset.test_size_intent} suffix={`${v}`} tone="amber" />)}
                    <p className="mt-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Test sentences per language</p>
                    {Object.entries(report.dataset.test_by_language).map(([k, v]) => <Bar key={k} label={k} value={v / report.dataset.test_size} suffix={`${v}`} tone="muted" />)}
                  </CardContent>
                </Card>
                <div className="flex flex-col gap-6">
                  <Card>
                    <CardHeader><CardTitle>How we measured</CardTitle></CardHeader>
                    <CardContent className="flex flex-col gap-2 text-sm leading-relaxed">
                      <p><b>1. Separate test set.</b> The model learns from the training sentences only. The test sentences are never used for training, and the page proves it: <Badge variant="secondary">{report.dataset.overlap_with_training} shared sentences</Badge>.</p>
                      <p><b>2. Cross-validation</b> chooses between models without touching the test set.</p>
                      <p><b>3. Several metrics, not just accuracy.</b> With uneven classes, accuracy alone can look good while a small class is ignored, so we also report precision, recall, F1 and the confusion matrix.</p>
                      <p><b>4. Same model as the app.</b> The numbers come from the exact classifier that answers farmers.</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader><CardTitle>Limits, stated honestly</CardTitle></CardHeader>
                    <CardContent>
                      <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed">
                        {report.limitations.map((l) => <li key={l}>{l}</li>)}
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>
    </div>
  );
}
