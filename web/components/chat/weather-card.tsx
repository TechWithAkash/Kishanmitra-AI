import { Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSun, Droplets, MapPin, Snowflake, Sun, Wind } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { BotReply } from "@/lib/types";

/** WMO weather code → icon. */
function iconFor(code: number): { Icon: LucideIcon; color: string } {
  if (code === 0 || code === 1) return { Icon: Sun, color: "text-amber-500" };
  if (code === 2) return { Icon: CloudSun, color: "text-amber-500" };
  if (code === 3) return { Icon: Cloud, color: "text-zinc-400" };
  if (code === 45 || code === 48) return { Icon: CloudFog, color: "text-zinc-400" };
  if (code >= 51 && code <= 57) return { Icon: CloudDrizzle, color: "text-sky-400" };
  if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82)) return { Icon: CloudRain, color: "text-sky-500" };
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return { Icon: Snowflake, color: "text-sky-300" };
  if (code >= 95) return { Icon: CloudLightning, color: "text-violet-500" };
  return { Icon: Cloud, color: "text-zinc-400" };
}

export function WeatherCard({ weather, lang }: { weather: NonNullable<BotReply["details"]["weather"]>; lang: string }) {
  const { current } = weather;
  const fmt = (iso: string) => {
    try {
      return new Date(iso + "T00:00:00").toLocaleDateString(lang, { weekday: "short", day: "numeric" });
    } catch {
      return iso;
    }
  };
  const now = current ? iconFor(current.code) : null;

  return (
    <Card size="sm" className="w-full max-w-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="size-4 text-primary" />
          <span className="truncate">{weather.place}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {current && now && (
          <div className="flex items-center gap-4">
            <now.Icon className={`size-12 shrink-0 ${now.color}`} aria-hidden />
            <div>
              <div className="text-4xl leading-none font-semibold tabular-nums">{Math.round(current.temp)}°C</div>
              <div className="mt-1 text-sm text-muted-foreground">{current.description}</div>
            </div>
            <dl className="ml-auto flex flex-col gap-1 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Droplets className="size-4" aria-hidden />
                <dt className="sr-only">Humidity</dt>
                <dd className="tabular-nums">{current.humidity}%</dd>
              </div>
              <div className="flex items-center gap-1.5">
                <Wind className="size-4" aria-hidden />
                <dt className="sr-only">Wind</dt>
                <dd className="tabular-nums">{Math.round(current.wind_kmh)} km/h</dd>
              </div>
            </dl>
          </div>
        )}

        <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          {weather.days.map((d, i) => {
            const { Icon, color } = iconFor(d.code);
            return (
              <div
                key={d.day}
                className="flex w-[4.6rem] shrink-0 flex-col items-center gap-1.5 rounded-lg bg-muted/50 p-2 text-center sm:flex-1"
              >
                <span className="text-xs text-muted-foreground">{i === 0 ? "Today" : fmt(d.day)}</span>
                <Icon className={`size-6 ${color}`} aria-label={d.description} />
                <span className="text-sm font-medium tabular-nums">
                  {Math.round(d.t_min)}° / {Math.round(d.t_max)}°
                </span>
                <Progress value={d.rain_chance} className="h-1.5 w-full" aria-label={`Rain chance ${d.rain_chance}%`} />
                <span className="text-xs tabular-nums text-muted-foreground">
                  {d.rain_chance}% · {d.rain_mm.toFixed(1)} mm
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
