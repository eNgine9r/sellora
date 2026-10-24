"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Play, MessageCircle, ShoppingBag, Truck, BarChart3, Users, Boxes, Megaphone, WalletCards } from "lucide-react";
import { PublicFooter, PublicHeader } from "@/components/public-layout";
import { useI18n } from "@/i18n/provider";
import styles from "./landing.module.css";

type Stage = {title:string; body:string; label:string; value:string; detail:string; action:string};
type Item = {title:string; body:string};
const stageIcons = [MessageCircle, ShoppingBag, Truck, BarChart3];
const capabilityIcons = [Users, Boxes, Megaphone, WalletCards];

export function LandingPage() {
  const { t, tr, locale } = useI18n();
  const text = (key:string) => t(`cinematicLanding.${key}`);
  const stages = tr<Stage[]>("cinematicLanding.stages");
  const [active, setActive] = useState(0);
  const scene = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = scene.current;
    if (!root || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const rect = root.getBoundingClientRect();
        if (rect.bottom > 0 && rect.top < innerHeight) root.style.setProperty("--scene-turn", `${Math.max(-3,Math.min(3,(rect.top / innerHeight)*3))}deg`);
      });
    };
    addEventListener("scroll", update, {passive:true}); update();
    return () => { removeEventListener("scroll",update); cancelAnimationFrame(frame); };
  }, []);
  const Icon = stageIcons[active];
  return <div className={styles.page}>
    <PublicHeader />
    <main>
      <section className={styles.hero} aria-labelledby="landing-title">
        <p className={styles.eyebrow}>{text("eyebrow")}</p>
        <h1 id="landing-title">{text("headline")}<br/><span>{text("accent")}</span></h1>
        <p className={styles.subtitle}>{text("subtitle")}</p>
        <div className={styles.actions}><a className={styles.primary} href="#workflow"><Play size={18} aria-hidden="true"/>{text("demo")}</a><a href="/login">{t("landing.primaryCta")}<ArrowRight size={16} aria-hidden="true"/></a></div>
        <p className={styles.pilot}>{text("pilot")}</p>
        <div className={styles.heroScene} ref={scene}>
          <Image src="/brand/landing-commerce-scene.webp" alt={text("heroAlt")} width={1500} height={850} priority sizes="(max-width: 768px) 100vw, 1200px" />
        </div>
      </section>
      <section id="workflow" className={`${styles.section} ${styles.story}`}>
        <div><p className={styles.eyebrow}>{t("landing.nav.workflow")}</p><h2>{text("storyTitle")}</h2><p className={styles.description}>{text("storyIntro")}</p>
          <div className={styles.steps} role="tablist" aria-label={text("storyTitle")}>
            {stages.map((stage,index)=><button key={stage.title} id={`stage-tab-${index}`} type="button" role="tab" aria-selected={active===index} aria-controls="stage-panel" tabIndex={active===index?0:-1} onClick={()=>setActive(index)} onKeyDown={event=>{let next=index;if(event.key==='ArrowRight')next=(index+1)%4;else if(event.key==='ArrowLeft')next=(index+3)%4;else if(event.key==='Home')next=0;else if(event.key==='End')next=3;else return;event.preventDefault();setActive(next);document.getElementById(`stage-tab-${next}`)?.focus();}}><span>{String(index+1).padStart(2,'0')}</span>{stage.title}</button>)}
          </div>
          <p className={styles.stageBody}>{stages[active].body}</p>
        </div>
        <div id="stage-panel" role="tabpanel" aria-labelledby={`stage-tab-${active}`} className={styles.demoPanel}>
          <div className={styles.panelHeader}><span>Sellora</span><span>{text("demoLabel")}</span></div>
          <div key={`${locale}-${active}`} className={styles.panelContent}><Icon size={32} aria-hidden="true"/><p className={styles.eyebrow}>{stages[active].label}</p><h3>{stages[active].value}</h3><p>{stages[active].detail}</p><button type="button" className={styles.primary} onClick={()=>setActive((active+1)%4)}>{stages[active].action}<ArrowRight size={18} aria-hidden="true"/></button></div>
        </div>
      </section>
      <section id="capabilities" className={styles.section}><p className={styles.eyebrow}>{t("landing.nav.capabilities")}</p><h2>{text("capTitle")}</h2><p className={styles.description}>{text("capIntro")}</p><div className={styles.features}>{tr<Item[]>("cinematicLanding.capabilities").map((item,index)=>{const FeatureIcon=capabilityIcons[index];return <article key={item.title}><FeatureIcon size={25} aria-hidden="true"/><h3>{item.title}</h3><p>{item.body}</p></article>;})}</div></section>
      <section id="integrations" className={styles.section}><p className={styles.eyebrow}>{t("landing.nav.integrations")}</p><h2>{text("intTitle")}</h2><p className={styles.description}>{text("intIntro")}</p><div className={styles.integrations}>{tr<Item[]>("cinematicLanding.integrations").map(item=><article key={item.title}><h3>{item.title}</h3><p>{item.body}</p></article>)}</div><p className={styles.note}>{text("sourceNote")}</p></section>
      <section className={styles.section}><h2>{text("faqTitle")}</h2><div className={styles.faq}>{tr<{q:string;a:string}[]>("cinematicLanding.faqs").map(item=><details key={item.q}><summary>{item.q}</summary><p>{item.a}</p></details>)}</div></section>
      <section className={`${styles.section} ${styles.final}`}><h2>{text("finalTitle")}</h2><p className={styles.description}>{text("finalBody")}</p><div className={styles.actions}><a className={styles.primary} href="#workflow">{text("demo")}<ArrowRight size={18} aria-hidden="true"/></a><a href="/login">{t("auth.login")}</a></div></section>
    </main><PublicFooter />
  </div>;
}
