"use client";

import { ArrowDown, ArrowUpRight, Check, Circle, MessageSquare, PackageCheck, ShoppingBag, Truck, Wallet } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import styles from "./landing.module.css";

/** Illustrative UI only. Never reads customer, order or integration data. */
export function CrmPreview({ compact = false }: { compact?: boolean }) {
  const { t, tr } = useI18n();
  const text = (key: string) => t(`scrollLanding.preview.${key}`);
  const costs = tr<{ label: string; value: string }[]>("scrollLanding.preview.costs");
  return <div className={`${styles.crmWorld} ${compact ? styles.compactWorld : ""}`} aria-label={text("label")}>
    <div className={styles.worldBrand} aria-hidden="true">Sellora<span>CRM</span></div>
    <article className={`${styles.crmLayer} ${styles.requestLayer}`} data-card-reveal data-crm-layer="0" id={compact ? undefined : "journey-request"}>
      <div className={styles.layerHeading}><span className={styles.layerIcon}><MessageSquare size={18} aria-hidden="true" /></span><h3>{text("request")}</h3><span className={styles.microNumber}>01</span></div>
      <div className={styles.person}><span className={styles.avatar} aria-hidden="true"><Circle size={20}/></span><div><strong>{text("customer")}</strong><span>{text("newCustomer")}</span></div><span className={styles.status}>{text("new")}</span></div>
      <p className={styles.message}>{text("message")}</p>
      <p className={styles.panelFoot}><Check size={14} aria-hidden="true"/>{text("customerContext")}</p>
    </article>
    <article className={`${styles.crmLayer} ${styles.orderLayer}`} data-card-reveal data-crm-layer="1" id={compact ? undefined : "journey-order"}>
      <div className={styles.layerHeading}><span className={styles.layerIcon}><ShoppingBag size={18} aria-hidden="true" /></span><h3>{text("order")}</h3><span className={styles.microNumber}>02</span></div>
      <div className={styles.orderItem}><span className={styles.productIcon}><ShoppingBag size={28} aria-hidden="true"/></span><div><strong>{text("product")}</strong><span>{text("variant")}</span></div><strong>{text("revenueValue")}</strong></div>
      <dl className={styles.miniRows}><div><dt>{text("stock")}</dt><dd><Check size={13} aria-hidden="true"/>{text("reserved")}</dd></div><div><dt>{text("payment")}</dt><dd>{text("paid")}</dd></div></dl>
      <p className={styles.panelFoot}><PackageCheck size={14} aria-hidden="true"/>{text("orderContext")}</p>
    </article>
    <article className={`${styles.crmLayer} ${styles.shipmentLayer}`} data-card-reveal data-crm-layer="2" id={compact ? undefined : "journey-shipment"}>
      <div className={styles.layerHeading}><span className={styles.layerIcon}><Truck size={18} aria-hidden="true" /></span><h3>{text("shipment")}</h3><span className={styles.microNumber}>03</span></div>
      <p className={styles.deliveryTitle}>{text("delivery")}</p><p className={styles.deliverySub}>{text("deliveryNote")}</p>
      <ol className={styles.deliveryTrack}>{tr<string[]>("scrollLanding.preview.deliverySteps").map((step, index) => <li key={step}><span><Check size={12} aria-hidden="true"/></span>{step}{index < 2 ? <ArrowDown size={12} className={styles.trackArrow} aria-hidden="true"/> : null}</li>)}</ol>
      <p className={styles.panelFoot}>{text("shipmentContext")}</p>
    </article>
    <article className={`${styles.crmLayer} ${styles.financeLayer}`} data-card-reveal data-crm-layer="3" id={compact ? undefined : "journey-finance"}>
      <div className={styles.layerHeading}><span className={styles.layerIcon}><Wallet size={18} aria-hidden="true" /></span><h3>{text("finance")}</h3><span className={styles.microNumber}>04</span></div>
      <dl className={styles.miniRows}><div><dt>{text("revenue")}</dt><dd>{text("revenueValue")}</dd></div>{costs.map(cost => <div key={cost.label}><dt>{cost.label}</dt><dd>{cost.value}</dd></div>)}</dl>
      <div className={styles.profit}><div><span>{text("profit")}</span><strong>{text("profitValue")}</strong></div><ArrowUpRight size={28} aria-hidden="true"/></div>
      <p className={styles.panelFoot}>{text("financeContext")}</p>
    </article>
  </div>;
}
