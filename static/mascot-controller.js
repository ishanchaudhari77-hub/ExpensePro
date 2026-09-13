(() => {
    "use strict";

    const RUPY_EVENT_NAME = "rupy:event";
    const KNOWN_STATES = [
        "idle",
        "login",
        "thinking",
        "warning",
        "error",
        "happy",
        "success",
        "celebrate",
        "lazy",
        "money-rain",
    ];
    const INACTIVITY_TIMEOUT_MS = 24000;

    const prefersReducedMotion = () => {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    };

    const normalizeState = (rawState) => {
        const normalized = String(rawState || "").trim().toLowerCase();
        if (!normalized) return "idle";
        if (normalized === "money" || normalized === "moneyrain") return "money-rain";
        if (normalized === "celebration") return "celebrate";
        if (normalized === "sleep") return "lazy";
        if (normalized === "focus" || normalized === "peek") return "thinking";
        if (KNOWN_STATES.includes(normalized)) return normalized;
        return "idle";
    };

    const removeStateClasses = (node) => {
        if (!node) return;
        KNOWN_STATES.forEach((state) => {
            node.classList.remove(`state-${state}`);
        });
    };

    function setupFloatingRupyWidget() {
        const widgetNode = document.querySelector("[data-rupy-float]");
        if (!widgetNode) return;

        const bubbleNode = widgetNode.querySelector("[data-rupy-float-bubble]");
        const imageNode = widgetNode.querySelector("[data-rupy-float-image]");
        const toggleNode = widgetNode.querySelector("[data-rupy-float-toggle]");
        const fxNode = widgetNode.querySelector("[data-rupy-float-fx]");

        const pageKey = String(
            widgetNode.dataset.rupyPage || document.body?.dataset?.endpoint || ""
        ).trim().toLowerCase();

        const imageMap = {
            idle: String(widgetNode.dataset.rupyImgIdle || imageNode?.getAttribute("src") || "").trim(),
            login: String(widgetNode.dataset.rupyImgLogin || "").trim(),
            thinking: String(widgetNode.dataset.rupyImgThinking || "").trim(),
            warning: String(widgetNode.dataset.rupyImgWarning || "").trim(),
            error: String(widgetNode.dataset.rupyImgError || "").trim(),
            happy: String(widgetNode.dataset.rupyImgHappy || "").trim(),
            celebrate: String(widgetNode.dataset.rupyImgCelebrate || "").trim(),
            success: String(widgetNode.dataset.rupyImgCelebrate || widgetNode.dataset.rupyImgHappy || "").trim(),
            lazy: String(widgetNode.dataset.rupyImgLazyRich || "").trim(),
            "money-rain": String(widgetNode.dataset.rupyImgMoneyRain || "").trim(),
        };

        const fxAssets = {
            coin: String(widgetNode.dataset.rupyCoin || "").trim(),
            coinGlow: String(widgetNode.dataset.rupyCoinGlow || "").trim(),
            particle: String(widgetNode.dataset.rupyParticle || "").trim(),
        };

        const preloadSet = new Set([
            ...Object.values(imageMap).filter(Boolean),
            ...Object.values(fxAssets).filter(Boolean),
        ]);
        preloadSet.forEach((src) => {
            const image = new Image();
            image.src = src;
        });

        const resolveStateImage = (stateName) => {
            const normalized = normalizeState(stateName);
            if (normalized === "success") {
                return imageMap.success || imageMap.happy || imageMap.celebrate || imageMap.idle;
            }
            if (normalized === "celebrate") {
                return imageMap.celebrate || imageMap.happy || imageMap.idle;
            }
            if (normalized === "money-rain") {
                return imageMap["money-rain"] || imageMap.celebrate || imageMap.happy || imageMap.idle;
            }
            if (normalized === "lazy") {
                return imageMap.lazy || imageMap.idle;
            }
            if (normalized === "login") {
                return imageMap.login || imageMap.idle;
            }
            return imageMap[normalized] || imageMap.idle;
        };

        let activeState = "idle";
        let bubbleTimer = null;
        let moodTimer = null;
        let inactivityTimer = null;

        const clearBubbleTimer = () => {
            if (!bubbleTimer) return;
            window.clearTimeout(bubbleTimer);
            bubbleTimer = null;
        };

        const clearMoodTimer = () => {
            if (!moodTimer) return;
            window.clearTimeout(moodTimer);
            moodTimer = null;
        };

        const speak = (message, autoCollapseMs = 5200) => {
            if (!bubbleNode) return;
            const text = String(message || "").trim();
            if (!text) return;

            clearBubbleTimer();
            bubbleNode.textContent = text;
            widgetNode.classList.remove("is-collapsed");
            bubbleTimer = window.setTimeout(() => {
                widgetNode.classList.add("is-collapsed");
            }, Math.max(1200, Number(autoCollapseMs) || 0));
        };

        const spawnBurstFx = () => {
            if (!fxNode || prefersReducedMotion()) return;
            fxNode.innerHTML = "";

            const coinSrc = fxAssets.coinGlow || fxAssets.coin;
            const particleSrc = fxAssets.particle;
            if (!coinSrc || !particleSrc) return;

            for (let index = 0; index < 9; index += 1) {
                const coin = document.createElement("img");
                coin.className = "rupy-fx-coin mode-burst";
                coin.src = coinSrc;
                const spread = (Math.random() * 112) - 56;
                const lift = -24 - (Math.random() * 80);
                const size = 12 + (Math.random() * 14);
                const rotation = (Math.random() * 300) - 150;
                coin.style.setProperty("--dx", `${spread.toFixed(1)}px`);
                coin.style.setProperty("--dy", `${lift.toFixed(1)}px`);
                coin.style.setProperty("--rot", `${rotation.toFixed(1)}deg`);
                coin.style.setProperty("--size", `${size.toFixed(1)}px`);
                fxNode.appendChild(coin);
            }

            for (let index = 0; index < 12; index += 1) {
                const particle = document.createElement("img");
                particle.className = "rupy-fx-particle mode-burst";
                particle.src = particleSrc;
                const spread = (Math.random() * 126) - 63;
                const lift = -16 - (Math.random() * 66);
                const size = 5 + (Math.random() * 8);
                particle.style.setProperty("--dx", `${spread.toFixed(1)}px`);
                particle.style.setProperty("--dy", `${lift.toFixed(1)}px`);
                particle.style.setProperty("--size", `${size.toFixed(1)}px`);
                fxNode.appendChild(particle);
            }

            window.setTimeout(() => {
                fxNode.innerHTML = "";
            }, 1300);
        };

        const spawnMoneyRainFx = () => {
            if (!fxNode || prefersReducedMotion()) return;
            fxNode.innerHTML = "";

            const coinSrc = fxAssets.coin || fxAssets.coinGlow;
            if (!coinSrc) return;

            for (let index = 0; index < 14; index += 1) {
                const coin = document.createElement("img");
                coin.className = "rupy-fx-coin mode-rain";
                coin.src = coinSrc;
                const startX = -52 + (Math.random() * 104);
                const endX = startX + ((Math.random() * 36) - 18);
                const rotation = (Math.random() * 420) - 210;
                const size = 10 + (Math.random() * 12);
                coin.style.animationDelay = `${(index * 46).toFixed(0)}ms`;
                coin.style.setProperty("--sx", `${startX.toFixed(1)}px`);
                coin.style.setProperty("--ex", `${endX.toFixed(1)}px`);
                coin.style.setProperty("--rot", `${rotation.toFixed(1)}deg`);
                coin.style.setProperty("--size", `${size.toFixed(1)}px`);
                fxNode.appendChild(coin);
            }

            window.setTimeout(() => {
                fxNode.innerHTML = "";
            }, 1800);
        };

        const applyState = (nextState, options = {}) => {
            const stateName = normalizeState(nextState);
            activeState = stateName;

            removeStateClasses(widgetNode);
            widgetNode.classList.add(`state-${stateName}`);

            const nextImage = resolveStateImage(stateName);
            if (imageNode && nextImage && String(imageNode.getAttribute("src") || "").trim() !== nextImage) {
                imageNode.setAttribute("src", nextImage);
            }

            if (options.message) {
                speak(options.message, options.messageDurationMs);
            }
            if (options.burst) {
                spawnBurstFx();
            }
            if (options.moneyRain) {
                spawnMoneyRainFx();
            }

            clearMoodTimer();
            const holdMs = Number(options.holdMs || 0);
            if (holdMs > 0 && stateName !== "lazy") {
                moodTimer = window.setTimeout(() => {
                    applyState("idle");
                }, holdMs);
            }
        };

        const resetInactivityTimer = () => {
            if (inactivityTimer) {
                window.clearTimeout(inactivityTimer);
                inactivityTimer = null;
            }
            inactivityTimer = window.setTimeout(() => {
                applyState("lazy", {
                    message: "No activity for a while. Let's get back to tracking.",
                    messageDurationMs: 4800,
                });
            }, INACTIVITY_TIMEOUT_MS);
        };

        const classifyToast = (toastType, rawMessage) => {
            const message = String(rawMessage || "").trim();
            const type = String(toastType || "info").trim().toLowerCase();
            const lowered = message.toLowerCase();

            if (lowered.includes("goal complete") || lowered.includes("celebration unlocked") || lowered.includes("goal completed")) {
                return {
                    state: "money-rain",
                    message: message || "Goal complete. Celebration unlocked.",
                    moneyRain: true,
                    holdMs: 3600,
                };
            }

            if (lowered.includes("goal deadline") || (lowered.includes("goal") && lowered.includes("overdue"))) {
                return {
                    state: "warning",
                    message: message || "Goal deadline warning.",
                    holdMs: 3600,
                };
            }

            if (lowered.includes("recurring goal") && lowered.includes("reset")) {
                return {
                    state: "thinking",
                    message: message || "Recurring goals reset. New cycle started.",
                    holdMs: 2800,
                };
            }

            if (type === "success") {
                return {
                    state: "happy",
                    message: message || "Nice! Budget under control.",
                    burst: true,
                    holdMs: 2600,
                };
            }
            if (type === "warning") {
                return {
                    state: "warning",
                    message: message || "Bro... you spent too much today.",
                    holdMs: 3400,
                };
            }
            if (type === "error") {
                return {
                    state: "error",
                    message: message || "Something failed. Try again.",
                    holdMs: 3400,
                };
            }
            return {
                state: "thinking",
                message: message || "Rupy is analyzing your spending pattern.",
                holdMs: 2400,
            };
        };

        const watchToasts = () => {
            const toastContainer = document.querySelector("[data-toast-container]");
            if (!toastContainer) return;

            const readToastType = (toastNode) => {
                if (!toastNode) return "info";
                if (toastNode.classList.contains("toast-success")) return "success";
                if (toastNode.classList.contains("toast-warning")) return "warning";
                if (toastNode.classList.contains("toast-error")) return "error";
                return "info";
            };

            const consumeToast = (toastNode) => {
                if (!toastNode || toastNode.dataset.rupyObserved === "1") return;
                toastNode.dataset.rupyObserved = "1";
                const copyNode = toastNode.querySelector(".toast-copy");
                const copyText = copyNode ? String(copyNode.textContent || "").trim() : "";
                const reaction = classifyToast(readToastType(toastNode), copyText);
                applyState(reaction.state, reaction);
            };

            toastContainer.querySelectorAll(".toast").forEach((toastNode) => {
                consumeToast(toastNode);
            });

            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((addedNode) => {
                        if (!(addedNode instanceof HTMLElement)) return;
                        if (addedNode.matches(".toast")) {
                            consumeToast(addedNode);
                            return;
                        }
                        const nestedToast = addedNode.querySelector(".toast");
                        if (nestedToast) consumeToast(nestedToast);
                    });
                });
            });
            observer.observe(toastContainer, { childList: true, subtree: true });
        };

        const applyInitialMood = () => {
            const spentPercent = Number(widgetNode.dataset.rupySpentPercent || 0);
            const budgetLeft = Number(widgetNode.dataset.rupyBudgetLeft || 0);
            const fromLoginTransition = document.body.classList.contains("from-login-transition");

            if (pageKey === "login" || pageKey === "register") {
                applyState("login", {
                    message: pageKey === "register"
                        ? "Let's create your account."
                        : "Welcome back. Track every rupee.",
                    holdMs: 2000,
                });
                return;
            }

            if (fromLoginTransition) {
                applyState("happy", {
                    message: "Welcome back. Track every rupee.",
                    burst: true,
                    holdMs: 2600,
                });
                return;
            }

            if (pageKey === "dashboard") {
                if (budgetLeft < 0 || spentPercent >= 90) {
                    applyState("warning", {
                        message: "Bro... you spent too much today.",
                        holdMs: 3600,
                    });
                    return;
                }
                if (spentPercent > 0 && spentPercent <= 60 && budgetLeft > 0) {
                    applyState("money-rain", {
                        message: "Nice! Budget under control.",
                        moneyRain: true,
                        holdMs: 3600,
                    });
                    return;
                }
                applyState("thinking", {
                    message: "Budget planning mode on. Keep your pace steady.",
                    holdMs: 2800,
                });
                return;
            }

            if (pageKey === "settings" || pageKey === "reports") {
                applyState("thinking", {
                    message: "Let's optimize your budget plan.",
                    holdMs: 2400,
                });
                return;
            }

            applyState("idle");
        };

        const handleRupyEvent = (eventType, payload = {}) => {
            const type = String(eventType || "").trim().toLowerCase();
            if (!type) return;

            if (type === "login_success") {
                applyState("happy", {
                    message: String(payload.message || "Welcome back. Track every rupee."),
                    burst: true,
                    holdMs: 2600,
                });
                return;
            }

            if (type === "high_spending" || type === "overspending") {
                applyState("warning", {
                    message: String(payload.message || "Bro... you spent too much today."),
                    holdMs: 3600,
                });
                return;
            }

            if (type === "budget_planning") {
                applyState("thinking", {
                    message: String(payload.message || "Budget planning mode on."),
                    holdMs: 2800,
                });
                return;
            }

            if (type === "saving_money" || type === "budget_under_control") {
                applyState("money-rain", {
                    message: String(payload.message || "Nice! Budget under control."),
                    moneyRain: true,
                    holdMs: 3400,
                });
                return;
            }

            if (type === "idle") {
                applyState("idle", {
                    message: String(payload.message || ""),
                });
                return;
            }
        };

        if (toggleNode) {
            toggleNode.addEventListener("click", () => {
                widgetNode.classList.toggle("is-collapsed");
            });
        }

        [
            { name: "pointerdown", options: { passive: true } },
            { name: "mousemove", options: { passive: true } },
            { name: "scroll", options: { passive: true } },
            { name: "touchstart", options: { passive: true } },
            { name: "keydown", options: undefined },
        ].forEach(({ name, options }) => {
            document.addEventListener(name, () => {
                if (activeState === "lazy") {
                    applyState("idle");
                }
                resetInactivityTimer();
            }, options);
        });

        const budgetForm = document.querySelector('form[action="/settings/budget"]');
        if (budgetForm) {
            budgetForm.addEventListener("focusin", () => {
                handleRupyEvent("budget_planning", { message: "Let's build a smarter budget plan." });
            });
            budgetForm.addEventListener("submit", () => {
                applyState("happy", {
                    message: "Nice! Budget plan saved.",
                    burst: true,
                    holdMs: 2600,
                });
            });
        }

        const expenseForm = document.querySelector('form[action="/add"]');
        if (expenseForm) {
            expenseForm.addEventListener("submit", () => {
                applyState("happy", {
                    message: "Nice! Expense captured.",
                    burst: true,
                    holdMs: 2000,
                });
            });
        }

        window.addEventListener(RUPY_EVENT_NAME, (event) => {
            const detail = event?.detail || {};
            handleRupyEvent(detail.type, detail);
        });

        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                applyState("lazy");
                return;
            }
            applyState("idle");
            resetInactivityTimer();
        });

        window.RupyMascot = {
            setState(stateName, options = {}) {
                applyState(stateName, options);
            },
            speak(message, autoCollapseMs = 5200) {
                speak(message, autoCollapseMs);
            },
            emit(type, payload = {}) {
                window.dispatchEvent(new CustomEvent(RUPY_EVENT_NAME, {
                    detail: {
                        type,
                        ...payload,
                    },
                }));
            },
        };

        watchToasts();
        applyInitialMood();
        resetInactivityTimer();
    }

    document.addEventListener("DOMContentLoaded", () => {
        setupFloatingRupyWidget();
    });
})();
