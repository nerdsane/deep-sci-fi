"use client";

import { useEffect, useRef, useCallback } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

// Register plugins (client-side only)
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, useGSAP);
}

// ============================================================================
// Types
// ============================================================================

export interface ScrollAnimationConfig {
  trigger: string | HTMLElement;
  start?: string;
  end?: string;
  scrub?: boolean | number;
  pin?: boolean;
  markers?: boolean;
  onEnter?: () => void;
  onLeave?: () => void;
  onEnterBack?: () => void;
  onLeaveBack?: () => void;
}

export type RevealEffect =
  | "fade-up"
  | "fade-down"
  | "fade-left"
  | "fade-right"
  | "scale"
  | "blur";

// ============================================================================
// useScrollTrigger - Basic scroll-triggered animation
// ============================================================================

export function useScrollTrigger(
  containerRef: React.RefObject<HTMLElement>,
  config: ScrollAnimationConfig
) {
  useGSAP(
    () => {
      if (!containerRef.current) return;

      ScrollTrigger.create({
        trigger: config.trigger,
        start: config.start ?? "top 80%",
        end: config.end ?? "bottom 20%",
        scrub: config.scrub ?? false,
        pin: config.pin ?? false,
        markers: config.markers ?? false,
        onEnter: config.onEnter,
        onLeave: config.onLeave,
        onEnterBack: config.onEnterBack,
        onLeaveBack: config.onLeaveBack,
      });
    },
    { scope: containerRef, dependencies: [config] }
  );
}

// ============================================================================
// useStaggeredReveal - Staggered reveal animation for grid items
// ============================================================================

export function useStaggeredReveal(
  containerRef: React.RefObject<HTMLElement>,
  itemSelector: string,
  options: {
    stagger?: number;
    duration?: number;
    y?: number;
    scale?: number;
    delay?: number;
  } = {}
) {
  useGSAP(
    () => {
      if (!containerRef.current) return;

      const items = containerRef.current.querySelectorAll(itemSelector);
      if (items.length === 0) return;

      // Set initial state
      gsap.set(items, {
        opacity: 0,
        y: options.y ?? 40,
        scale: options.scale ?? 0.95,
      });

      // Animate on scroll
      gsap.to(items, {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: options.duration ?? 0.6,
        stagger: options.stagger ?? 0.1,
        delay: options.delay ?? 0,
        ease: "power2.out",
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top 85%",
          toggleActions: "play none none reverse",
        },
      });
    },
    { scope: containerRef, dependencies: [itemSelector] }
  );
}

// ============================================================================
// useParallax - Parallax effect on scroll
// ============================================================================

export function useParallax(
  elementRef: React.RefObject<HTMLElement>,
  options: {
    speed?: number;
    direction?: "vertical" | "horizontal";
  } = {}
) {
  useGSAP(
    () => {
      if (!elementRef.current) return;

      const speed = options.speed ?? 0.3;
      const prop = options.direction === "horizontal" ? "x" : "y";

      gsap.to(elementRef.current, {
        [prop]: () => speed * window.innerHeight * 0.3,
        ease: "none",
        scrollTrigger: {
          trigger: elementRef.current,
          start: "top bottom",
          end: "bottom top",
          scrub: true,
        },
      });
    },
    { scope: elementRef }
  );
}

// ============================================================================
// useFadeInOnScroll - Fade in elements when they enter viewport
// ============================================================================

export function useFadeInOnScroll(
  elementRef: React.RefObject<HTMLElement>,
  effect: RevealEffect = "fade-up",
  options: {
    duration?: number;
    delay?: number;
    ease?: string;
  } = {}
) {
  useGSAP(
    () => {
      if (!elementRef.current) return;

      const duration = options.duration ?? 0.8;
      const delay = options.delay ?? 0;
      const ease = options.ease ?? "power2.out";

      let fromVars: gsap.TweenVars = { opacity: 0 };

      switch (effect) {
        case "fade-up":
          fromVars = { opacity: 0, y: 40 };
          break;
        case "fade-down":
          fromVars = { opacity: 0, y: -40 };
          break;
        case "fade-left":
          fromVars = { opacity: 0, x: 40 };
          break;
        case "fade-right":
          fromVars = { opacity: 0, x: -40 };
          break;
        case "scale":
          fromVars = { opacity: 0, scale: 0.9 };
          break;
        case "blur":
          fromVars = { opacity: 0, filter: "blur(10px)" };
          break;
      }

      gsap.set(elementRef.current, fromVars);

      gsap.to(elementRef.current, {
        opacity: 1,
        y: 0,
        x: 0,
        scale: 1,
        filter: "blur(0px)",
        duration,
        delay,
        ease,
        scrollTrigger: {
          trigger: elementRef.current,
          start: "top 85%",
          toggleActions: "play none none reverse",
        },
      });
    },
    { scope: elementRef, dependencies: [effect] }
  );
}

// ============================================================================
// useHeroParallax - Special parallax for hero sections
// ============================================================================

export function useHeroParallax(
  heroRef: React.RefObject<HTMLElement>,
  options: {
    bgSpeed?: number;
    titleSpeed?: number;
    fadeOutOnScroll?: boolean;
  } = {}
) {
  useGSAP(
    () => {
      if (!heroRef.current) return;

      const bgSpeed = options.bgSpeed ?? 0.5;
      const titleSpeed = options.titleSpeed ?? 0.3;
      const fadeOut = options.fadeOutOnScroll ?? true;

      // Find child elements
      const bg = heroRef.current.querySelector("[data-parallax-bg]");
      const title = heroRef.current.querySelector("[data-parallax-title]");
      const content = heroRef.current.querySelector("[data-parallax-content]");

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: heroRef.current,
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });

      if (bg) {
        tl.to(bg, { y: window.innerHeight * bgSpeed }, 0);
      }

      if (title) {
        tl.to(title, { y: window.innerHeight * titleSpeed }, 0);
      }

      if (content && fadeOut) {
        tl.to(content, { opacity: 0, y: 50 }, 0);
      }
    },
    { scope: heroRef }
  );
}

// ============================================================================
// usePinSection - Pin section while scrolling through content
// ============================================================================

export function usePinSection(
  sectionRef: React.RefObject<HTMLElement>,
  options: {
    pinSpacing?: boolean;
    endOffset?: string;
  } = {}
) {
  useGSAP(
    () => {
      if (!sectionRef.current) return;

      ScrollTrigger.create({
        trigger: sectionRef.current,
        start: "top top",
        end: options.endOffset ?? "+=100%",
        pin: true,
        pinSpacing: options.pinSpacing ?? true,
      });
    },
    { scope: sectionRef }
  );
}

// ============================================================================
// Utilities
// ============================================================================

export function refreshScrollTrigger() {
  ScrollTrigger.refresh();
}

export function killAllScrollTriggers() {
  ScrollTrigger.getAll().forEach((st) => st.kill());
}

// ============================================================================
// useCardHoverAnimation - GSAP hover animation for cards
// ============================================================================

export function useCardHoverAnimation(
  cardRef: React.RefObject<HTMLElement>,
  options: {
    scale?: number;
    duration?: number;
    glowColor?: string;
  } = {}
) {
  const hoverTween = useRef<gsap.core.Tween | null>(null);

  const onMouseEnter = useCallback(() => {
    if (!cardRef.current) return;

    hoverTween.current?.kill();
    hoverTween.current = gsap.to(cardRef.current, {
      scale: options.scale ?? 1.02,
      duration: options.duration ?? 0.3,
      ease: "power2.out",
      boxShadow: `0 0 30px ${options.glowColor ?? "rgba(0, 255, 204, 0.3)"}`,
    });
  }, [cardRef, options]);

  const onMouseLeave = useCallback(() => {
    if (!cardRef.current) return;

    hoverTween.current?.kill();
    hoverTween.current = gsap.to(cardRef.current, {
      scale: 1,
      duration: options.duration ?? 0.3,
      ease: "power2.out",
      boxShadow: "0 0 0 transparent",
    });
  }, [cardRef, options]);

  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    card.addEventListener("mouseenter", onMouseEnter);
    card.addEventListener("mouseleave", onMouseLeave);

    return () => {
      card.removeEventListener("mouseenter", onMouseEnter);
      card.removeEventListener("mouseleave", onMouseLeave);
      hoverTween.current?.kill();
    };
  }, [cardRef, onMouseEnter, onMouseLeave]);
}
