"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Play, MessageCircle, ShoppingBag, Truck, BarChart3, Users, Boxes, Megaphone, WalletCards } from "lucide-react";
import { PublicFooter, PublicHeader } from "@/components/public-layout";
import { useI18n } from "@/i18n/provider";
import styles from "./landing.module.css";

type Stage = { title: string; body: string; label: string; value: string; detail: string; action: string };
type Item = {title:string; body:string};
const stageIcons = [MessageCircle, ShoppingBag, Truck, BarChart3];
const capabilityIcons = [Users, Boxes, Megaphone, WalletCards];

export function LandingPage() {
  const { t, tr, locale } = useI18n();
  const text = (key:string) => t(`cinematicLanding.${key}`);
  const stages = tr<Stage[]>("cinematicLanding.stages");
  const [active, setActive] = useState(0);
  const page = useRef<HTMLDivElement>(null);
  const scene = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [motionPaused, setMotionPaused] = useState(false);

  useEffect(() => {
    const root = page.current;
    const hero = scene.current;
    if (!root || !hero) return;
    const preference = matchMedia("(prefers-reduced-motion: reduce)");
    const pointer = matchMedia("(pointer: fine)");
    let frame = 0;
    const allowed = () => !motionPaused && !preference.matches && innerWidth >= 768;
    const reset = () => {
      ["--hero-x", "--hero-y", "--hero-lift", "--panel-turn"].forEach(key => root.style.removeProperty(key));
    };
    const paint = () => {
      frame = 0;
      root.dataset.motion = allowed() ? "on" : "off";
      if (!allowed()) { reset(); return; }
      if (document.hidden) return;
      const rect = hero.getBoundingClientRect();
      if (rect.bottom > 0 && rect.top < innerHeight) {
        const progress = Math.max(-1, Math.min(1, (rect.top - innerHeight * 0.3) / innerHeight));
        root.style.setProperty("--hero-x", `${progress * -5}deg`);
        root.style.setProperty("--hero-lift", `${progress * -22}px`);
      }
      const bounds = panel.current?.getBoundingClientRect();
      if (bounds && bounds.bottom > 0 && bounds.top < innerHeight) {
        root.style.setProperty("--panel-turn", `${Math.max(-4, Math.min(4, bounds.top / innerHeight * -6))}deg`);
      }
    };
    const schedule = () => {
      if (document.hidden) { cancelAnimationFrame(frame); frame = 0; return; }
      if (!frame) frame = requestAnimationFrame(paint);
    };
    const move = (event: PointerEvent) => {
      if (!allowed() || !pointer.matches || document.hidden) return;
      const rect = hero.getBoundingClientRect();
      const relative = Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1));
      root.style.setProperty("--hero-y", `${relative * 3}deg`);
    };
    const leave = () => root.style.removeProperty("--hero-y");
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    document.addEventListener("visibilitychange", schedule);
    preference.addEventListener("change", schedule);
    hero.addEventListener("pointermove", move, { passive: true });
    hero.addEventListener("pointerleave", leave);
    paint();
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener("scroll", schedule);
      removeEventListener("resize", schedule);
      document.removeEventListener("visibilitychange", schedule);
      preference.removeEventListener("change", schedule);
      hero.removeEventListener("pointermove", move);
      hero.removeEventListener("pointerleave", leave);
      reset();
    };
  }, [motionPaused]);
  const Icon = stageIcons[active];
  return <div className={styles.page} ref={page}>
    <PublicHeader />
    <main>
      <section className={styles.hero} aria-labelledby="landing-title">
        <p className={styles.eyebrow}>{text("eyebrow")}</p>
        <h1 id="landing-title">{text("headline")}<br/><span>{text("accent")}</span></h1>
        <p className={styles.subtitle}>{text("subtitle")}</p>
        <div className={styles.actions}><a className={styles.primary} href="#workflow"><Play size={18} aria-hidden="true"/>{text("demo")}</a><a href="/login">{t("landing.primaryCta")}<ArrowRight size={16} aria-hidden="true"/></a></div>
        <p className={styles.pilot}>{text("pilot")}</p>
        <button type="button" className={styles.motionControl} aria-pressed={motionPaused} onClick={() => setMotionPaused(value => !value)}>{text("motionLabel")}</button>
        <div className={styles.heroScene} ref={scene}>
          <Image src={locale === "en" ? "/brand/landing-commerce-scene-en.webp" : "/brand/landing-commerce-scene.webp"} alt={text("heroAlt")} width={1672} height={941} priority sizes="(max-width: 768px) 100vw, 1200px" />
        </div>
        <p className={styles.caption}>{text("heroCaption")}</p>
      </section>
      <section id="workflow" className={`${styles.section} ${styles.story}`}>
        <div><p className={styles.eyebrow}>{t("landing.nav.workflow")}</p><h2>{text("storyLead")}<br/>{text("storyRest")}</h2><p className={styles.description}>{text("storyIntro")}</p>
          <div className={styles.steps} role="tablist" aria-label={text("storyTitle")}>
            {stages.map((stage,index)=><button key={stage.title} id={`stage-tab-${index}`} type="button" role="tab" aria-selected={active===index} aria-controls="stage-panel" tabIndex={active===index?0:-1} onClick={()=>setActive(index)} onKeyDown={event=>{let next=index;if(event.key==='ArrowRight')next=(index+1)%4;else if(event.key==='ArrowLeft')next=(index+3)%4;else if(event.key==='Home')next=0;else if(event.key==='End')next=3;else return;event.preventDefault();setActive(next);document.getElementById(`stage-tab-${next}`)?.focus();}}><span>{String(index+1).padStart(2,'0')}</span>{stage.title}</button>)}
          </div>
          <p className={styles.stageBody}>{stages[active].body}</p>
        </div>
        <div className={styles.workspaceScene}>
          <Image className={styles.shipmentArt} src="/brand/landing-shipment-scene.webp" alt="" width={1100} height={800} sizes="(max-width: 800px) 90vw, 650px" />
          <div id="stage-panel" ref={panel} role="tabpanel" tabIndex={0} aria-labelledby={`stage-tab-${active}`} className={styles.demoPanel}>
            <div className={styles.panelHeader}><span>Sellora</span><span>{text("demoLabel")}</span></div>
            <div className={styles.workspaceBody}>
              <div className={styles.demoRail} aria-hidden="true">{stageIcons.map((RailIcon,index) => <RailIcon key={index} size={18} className={index === active ? styles.railActive : undefined} />)}</div>
              <div className={styles.panelContent}>
                <div className={styles.panelStage} key={`${locale}-${active}`}>
                  <p className={styles.eyebrow}><Icon size={16} aria-hidden="true"/>{stages[active].label}</p>
                  <h3>{stages[active].value}</h3>
                  <p className={styles.panelDetail}>{stages[active].detail}</p>
                </div>
                <div className={styles.orderContext}>
                  <p className={styles.contextTitle}>{text("contextLabel")}</p>
                  <dl>
                    <div><dt>{text("customerLabel")}</dt><dd>{text("customerValue")}</dd></div>
                    <div><dt>{text("productLabel")}</dt><dd>{text("productValue")}</dd></div>
                    <div><dt>{active === 3 ? text("costLabel") : text("paymentLabel")}</dt><dd>{active === 3 ? text("costValue") : text("paymentValue")}</dd></div>
                    <div><dt>{active === 2 ? text("shippingLabel") : text("amountLabel")}</dt><dd>{active === 2 ? text("shippingValue") : text("amountValue")}</dd></div>
                  </dl>
                </div>
                <button type="button" className={styles.primary} onClick={() => setActive((active + 1) % stages.length)}>{stages[active].action}<ArrowRight size={18} aria-hidden="true"/></button>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section id="capabilities" className={styles.section}><p className={styles.eyebrow}>{t("landing.nav.capabilities")}</p><h2>{text("capTitle")}</h2><p className={styles.description}>{text("capIntro")}</p><div className={styles.features}>{tr<Item[]>("cinematicLanding.capabilities").map((item,index)=>{const FeatureIcon=capabilityIcons[index];return <article key={item.title}><FeatureIcon size={25} aria-hidden="true"/><h3>{item.title}</h3><p>{item.body}</p></article>;})}</div></section>
      <section id="integrations" className={styles.section}><p className={styles.eyebrow}>{t("landing.nav.integrations")}</p><h2>{text("intTitle")}</h2><p className={styles.description}>{text("intIntro")}</p><div className={styles.integrations}>{tr<Item[]>("cinematicLanding.integrations").map(item=><article key={item.title}><h3>{item.title}</h3><p>{item.body}</p></article>)}</div><p className={styles.note}>{text("sourceNote")}</p></section>
      <section className={styles.section}><h2>{text("faqTitle")}</h2><div className={styles.faq}>{tr<{q:string;a:string}[]>("cinematicLanding.faqs").map(item=><details key={item.q}><summary>{item.q}</summary><p>{item.a}</p></details>)}</div></section>
      <section className={`${styles.section} ${styles.final}`}><h2>{text("finalTitle")}</h2><p className={styles.description}>{text("finalBody")}</p><div className={styles.actions}><a className={styles.primary} href="#workflow">{text("demo")}<ArrowRight size={18} aria-hidden="true"/></a><a href="/login">{t("auth.login")}</a></div></section>
    </main><PublicFooter />
  </div>;
}
