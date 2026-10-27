"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowRight, Boxes, Check, Layers3, MessageSquare, MoveDown, Pause, Play, ShoppingBag, Truck, Users, Wallet } from "lucide-react";
import { PublicFooter, PublicHeader } from "@/components/public-layout";
import { CrmPreview } from "@/components/crm-preview";
import { useI18n } from "@/i18n/provider";
import styles from "./landing.module.css";

type Item = { title: string; body: string };
type Chapter = { title: string; heading: string; body: string };
const chapterIcons = [Layers3, MessageSquare, ShoppingBag, Truck, Wallet];
const capabilityIcons = [Users, ShoppingBag, Boxes, Truck, Wallet, Layers3];
const clamp = (n: number, min = 0, max = 1) => Math.max(min, Math.min(max, n));
const overview = [
  [-155, -112, -20, 9, -12, .79, 1],
  [170, -85, 35, 6, -12, .83, 1],
  [-160, 142, 5, 9, -12, .77, 1],
  [175, 98, 70, 6, -12, .70, 1],
];
// Per-layer camera poses: x, y, z, rotateX, rotateY, scale, opacity.
function pose(layer: number, chapter: number) {
  if (!chapter) return overview[layer];
  if (layer === chapter - 1) return [0, 10, 150, 0, 0, 1.12, 1];
  return [(layer % 2 ? 1 : -1) * 265, (layer < chapter - 1 ? -1 : 1) * 155, -180, 12, layer % 2 ? -22 : 22, .64, .24];
}

export function LandingPage() {
  const { t, tr, locale } = useI18n();
  const text = (key: string) => t(`scrollLanding.${key}`);
  const chapters = tr<Chapter[]>("scrollLanding.chapters");
  const [active, setActive] = useState(0);
  const [motionPaused, setMotionPaused] = useState(false);
  const page = useRef<HTMLDivElement>(null);
  const journey = useRef<HTMLElement>(null);
  const activeRef = useRef(0);

  useEffect(() => {
    const root = page.current;
    const section = journey.current;
    if (!root || !section) return;
    const preference = matchMedia("(prefers-reduced-motion: reduce)");
    const desktop = matchMedia("(min-width: 900px) and (min-height: 760px)");
    const layers = [...section.querySelectorAll<HTMLElement>("[data-crm-layer]")];
    const world = section.querySelector<HTMLElement>(`.${styles.crmWorld}`);
    let frame = 0;
    let visible = true;
    const enabled = () => !motionPaused && !preference.matches;
    const paint = () => {
      frame = 0;
      if (document.hidden || !visible || !enabled() || !desktop.matches) return;
      const bounds = section.getBoundingClientRect();
      const range = Math.max(1, section.offsetHeight - innerHeight + 76);
      const progress = clamp((76 - bounds.top) / range) * 4;
      const from = Math.min(3, Math.floor(progress));
      const fraction = progress - from;
      const blend = fraction * fraction * (3 - 2 * fraction);
      const next = Math.round(progress);
      if (next !== activeRef.current) { activeRef.current = next; setActive(next); }
      section.style.setProperty("--progress", `${progress / 4 * 100}%`);
      world?.style.setProperty("--camera-y", `${Math.sin(progress * Math.PI / 2) * -5}deg`);
      layers.forEach((layer, index) => {
        const a = pose(index, from);
        const b = pose(index, from + 1);
        const p = a.map((value, i) => value + (b[i] - value) * blend);
        layer.style.transform = `translate3d(${p[0]}px, ${p[1]}px, ${p[2]}px) rotateX(${p[3]}deg) rotateY(${p[4]}deg) scale(${p[5]})`;
        layer.style.opacity = String(p[6]);
        layer.style.zIndex = index === next - 1 ? "5" : "1";
      });
    };
    const schedule = () => { if (!frame && !document.hidden) frame = requestAnimationFrame(paint); };
    const configure = () => {
      root.dataset.motion = enabled() ? "on" : "off";
      section.dataset.animated = String(enabled() && desktop.matches);
      if (!enabled() || !desktop.matches) {
        layers.forEach(layer => { layer.style.removeProperty("transform"); layer.style.removeProperty("opacity"); layer.style.removeProperty("z-index"); });
        section.style.removeProperty("--progress");
        world?.style.removeProperty("--camera-y");
        activeRef.current = 0; setActive(0);
      }
      schedule();
    };
    const visibility = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; if (visible) schedule(); }, { rootMargin: "200px" });
    visibility.observe(section);
    const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { (entry.target as HTMLElement).dataset.revealed = "true"; reveal.unobserve(entry.target); }
    }), { threshold: .12 });
    root.querySelectorAll("[data-reveal], [data-card-reveal]").forEach(el => reveal.observe(el));
    root.dataset.enhanced = "true";
    configure();
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    document.addEventListener("visibilitychange", schedule);
    preference.addEventListener("change", configure);
    desktop.addEventListener("change", configure);
    return () => {
      cancelAnimationFrame(frame); visibility.disconnect(); reveal.disconnect();
      removeEventListener("scroll", schedule); removeEventListener("resize", schedule);
      document.removeEventListener("visibilitychange", schedule);
      preference.removeEventListener("change", configure); desktop.removeEventListener("change", configure);
    };
  }, [motionPaused]);

  function goToChapter(index: number) {
    const section = journey.current;
    if (!section) return;
    const animated = section.dataset.animated === "true";
    const behavior = motionPaused || matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";
    if (animated) {
      const range = section.offsetHeight - innerHeight + 76;
      window.scrollTo({ top: section.getBoundingClientRect().top + scrollY - 76 + range * index / 4, behavior });
    } else if (index) section.querySelectorAll<HTMLElement>("[data-crm-layer]")[index - 1]?.scrollIntoView({ behavior, block: "center" });
    else section.scrollIntoView({ behavior, block: "start" });
  }

  return <div className={styles.page} ref={page}>
    <PublicHeader />
    <main>
      <section className={styles.hero} aria-labelledby="landing-title">
        <p className={styles.eyebrow}><span/>{text("eyebrow")}</p>
        <h1 id="landing-title">{text("headline")}<br/><span>{text("accent")}</span></h1>
        <p className={styles.subtitle}>{text("subtitle")}</p>
        <div className={styles.actions}><a className={styles.primary} href="#workflow">{text("explore")}<ArrowDown size={18} aria-hidden="true"/></a><a className={styles.secondary} href="/login">{t("auth.login")}<ArrowRight size={17} aria-hidden="true"/></a></div>
        <div className={styles.heroMeta}><span><Check size={14} aria-hidden="true"/>{text("pilot")}</span><button type="button" aria-pressed={motionPaused} onClick={() => setMotionPaused(v => !v)}>{motionPaused ? <Play size={13} aria-hidden="true"/> : <Pause size={13} aria-hidden="true"/>}{text(motionPaused ? "enableMotion" : "reduceMotion")}</button></div>
        <a className={styles.scrollHint} href="#workflow"><MoveDown size={17} aria-hidden="true"/>{text("scrollHint")}</a>
      </section>
      <section id="workflow" ref={journey} className={styles.journey} data-animated="false" aria-label={text("journeyLabel")}>
        <div className={styles.journeySticky}>
          <div className={styles.journeyCopy}>
            <p className={styles.eyebrow}>{text("journeyEyebrow")}</p>
            <div className={styles.chapterText} key={`${locale}-${active}`}><p className={styles.chapterCount}>{String(active + 1).padStart(2, "0")} <span>/ 05</span></p><h2>{chapters[active].heading}</h2><p>{chapters[active].body}</p></div>
            <nav className={styles.chapterNav} aria-label={text("journeyLabel")}>{chapters.map((chapter, i) => { const Icon = chapterIcons[i]; return <button type="button" key={chapter.title} aria-current={active === i ? "step" : undefined} onClick={() => goToChapter(i)}><Icon size={16} aria-hidden="true"/><span>{chapter.title}</span><span className={styles.navDot}/></button>; })}</nav>
            <p className={styles.demoNote}>{text("demoNote")}</p>
          </div>
          <div className={styles.journeyVisual}><CrmPreview /><div className={styles.sceneCaption}><span>Sellora / CRM</span><span>{text("sceneCaption")}</span></div></div>
          <div className={styles.journeyProgress} aria-hidden="true"><span/></div>
        </div>
      </section>
      <section id="capabilities" className={styles.section}>
        <div className={styles.sectionIntro} data-reveal><p className={styles.eyebrow}>{t("landing.nav.capabilities")}</p><h2>{text("capTitle")}</h2><p className={styles.description}>{text("capIntro")}</p></div>
        <div className={styles.features}>{tr<Item[]>("scrollLanding.capabilities").map((item, i) => { const Icon = capabilityIcons[i]; return <article key={item.title} data-reveal><span className={styles.featureNumber}>0{i + 1}</span><Icon size={25} aria-hidden="true"/><h3>{item.title}</h3><p>{item.body}</p></article>; })}</div>
      </section>
      <section id="integrations" className={`${styles.section} ${styles.integrationSection}`}>
        <div data-reveal><p className={styles.eyebrow}>{t("landing.nav.integrations")}</p><h2>{text("intTitle")}</h2><p className={styles.description}>{text("intIntro")}</p></div>
        <div className={styles.integrations}>{tr<(Item & { status: string })[]>("scrollLanding.integrations").map(item => <article key={item.title} data-reveal><span className={styles.integrationStatus}>{item.status}</span><h3>{item.title}</h3><p>{item.body}</p></article>)}</div>
        <p className={styles.note}>{text("integrationNote")}</p>
      </section>
      <section className={styles.section}><div data-reveal><p className={styles.eyebrow}>{text("faqEyebrow")}</p><h2>{text("faqTitle")}</h2></div><div className={styles.faq}>{tr<{q: string; a: string}[]>("scrollLanding.faqs").map(item => <details key={item.q}><summary>{item.q}</summary><p>{item.a}</p></details>)}</div></section>
      <section className={`${styles.section} ${styles.final}`} data-reveal><p className={styles.eyebrow}>Sellora CRM</p><h2>{text("finalTitle")}</h2><p className={styles.description}>{text("finalBody")}</p><a className={styles.primary} href="/login">{t("auth.login")}<ArrowRight size={18} aria-hidden="true"/></a></section>
    </main>
    <PublicFooter />
  </div>;
}
