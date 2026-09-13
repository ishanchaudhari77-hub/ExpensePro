(() => {
    "use strict";

    if (window.__RUPY_MASCOT_CONTROLLER_READY__) return;
    window.__RUPY_MASCOT_CONTROLLER_READY__ = true;

    const RUPY_EVENT_NAME = "rupy:event";
    const INACTIVITY_TIMEOUT_MS = 24000;
    const RANDOM_TIP_INTERVAL_MS = 30000;
    const DEFAULT_ASSET_BASE = "/static/mascot/rupy/";

    const STATE_FILE_MAP = {
        idle: "rupy_idle.png",
        hello: "rupy_hello.png",
        login: "rupy_login.png",
        happy: "rupy_happy.png",
        thinking: "rupy_thinking.png",
        warning: "rupy_warning.png",
        confused: "rupy_confused.png",
        celebration: "rupy_celebration.png",
        sad: "rupy_sad.png",
        angry: "rupy_angry.png",
        error: "rupy_error.png",
        loading: "rupy_loading.png",
        notification: "rupy_notification.png",
        "lazy-rich": "rupy_lazy_rich.png",
        "money-rain": "rupy_money_rain.png",
        proud: "rupy_proud.png",
        wink: "rupy_wink.png",
        thumbs_up: "rupy_thumbs_up.png",
        broke: "rupy_broke.png",
        sunglasses: "rupy_sunglasses.png",
        coffee_spend: "rupy_coffee_spend.png",
        analyzing_chart: "rupy_analyzing_chart.png",
        lightbulb_idea: "rupy_lightbulb_idea.png",
    };

    const KNOWN_STATES = [
        "idle",
        "hello",
        "login",
        "happy",
        "thinking",
        "warning",
        "confused",
        "celebration",
        "sad",
        "angry",
        "error",
        "loading",
        "notification",
        "lazy-rich",
        "money-rain",
    ];

    const STATE_ALIASES = {
        celebrate: "celebration",
        success: "celebration",
        lazy: "lazy-rich",
        sleep: "lazy-rich",
        moneyrain: "money-rain",
        money_rain: "money-rain",
        login_page: "hello",
    };

    const DEFAULT_MESSAGES = {
        hello: "Welcome back! Track every rupee.",
        happy: "Nice! Expense added.",
        warning: "Bro... budget cross ho gaya.",
        thinking: "Let me analyze your spending.",
        confused: "Something looks unusual.",
        celebration: "Savings goal achieved!",
        sad: "Spending is high today.",
        proud: "Great job staying under budget!",
        loading: "Analyzing your spending data...",
        notification: "Rupy has an update for you.",
        error: "Something went wrong. Try again.",
        "lazy-rich": "No activity detected. Chalo budget check karte hain.",
        idle: "Track every rupee.",
    };

    const RANDOM_TIPS = [
        "Track every rupee.",
        "Budget planning saves money.",
        "Coffee spending check karo.",
        "Small daily cuts create big monthly savings.",
        "Review categories weekly for better control.",
    ];

    const prefersReducedMotion = () => {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    };

    const normalizeState = (rawState) => {
        const normalized = String(rawState || "").trim().toLowerCase();
        if (!normalized) return "idle";
        if (STATE_ALIASES[normalized]) return STATE_ALIASES[normalized];
        if (KNOWN_STATES.includes(normalized)) return normalized;
        return "idle";
    };

    const normalizeAssetBase = (rawBase) => {
        const base = String(rawBase || "").trim();
        if (!base) return "";
        return base.endsWith("/") ? base : `${base}/`;
    };

    const deriveAssetBase = (widgetNode, imageNode) => {
        const explicitBase = normalizeAssetBase(widgetNode.getAttribute("data-rupy-asset-base"));
        if (explicitBase) return explicitBase;

        const idleFromDataset = String(widgetNode.getAttribute("data-rupy-img-idle") || "").trim();
        const idleFromImage = String(imageNode?.getAttribute("src") || "").trim();
        const source = idleFromDataset || idleFromImage;
        if (!source) return DEFAULT_ASSET_BASE;

        const withoutQuery = source.split("?")[0];
        const slashIndex = withoutQuery.lastIndexOf("/");
        if (slashIndex === -1) return DEFAULT_ASSET_BASE;
        return withoutQuery.slice(0, slashIndex + 1);
    };

    const datasetStateAsset = (widgetNode, stateName) => {
        const value = String(widgetNode.getAttribute(`data-rupy-img-${stateName}`) || "").trim();
        return value;
    };

    const buildImageMap = (widgetNode, imageNode) => {
        const assetBase = deriveAssetBase(widgetNode, imageNode);
        const map = {};

        Object.entries(STATE_FILE_MAP).forEach(([stateName, fileName]) => {
            map[stateName] = `${assetBase}${fileName}`;
        });

        const overrides = {
            idle: datasetStateAsset(widgetNode, "idle"),
            hello: datasetStateAsset(widgetNode, "hello"),
            login: datasetStateAsset(widgetNode, "login"),
            happy: datasetStateAsset(widgetNode, "happy"),
            thinking: datasetStateAsset(widgetNode, "thinking"),
            warning: datasetStateAsset(widgetNode, "warning"),
            confused: datasetStateAsset(widgetNode, "confused"),
            celebration: datasetStateAsset(widgetNode, "celebration") || datasetStateAsset(widgetNode, "celebrate"),
            sad: datasetStateAsset(widgetNode, "sad"),
            angry: datasetStateAsset(widgetNode, "angry"),
            error: datasetStateAsset(widgetNode, "error"),
            loading: datasetStateAsset(widgetNode, "loading") || datasetStateAsset(widgetNode, "thinking"),
            notification: datasetStateAsset(widgetNode, "notification"),
            "lazy-rich": datasetStateAsset(widgetNode, "lazy-rich") || datasetStateAsset(widgetNode, "lazy"),
            "money-rain": datasetStateAsset(widgetNode, "money-rain"),
            proud: datasetStateAsset(widgetNode, "proud"),
        };

        Object.entries(overrides).forEach(([key, value]) => {
            if (value) map[key] = value;
        });

        return map;
    };

    const removeStateClasses = (node) => {
        if (!node) return;
        [
            ...KNOWN_STATES,
            "success",
            "celebrate",
            "lazy",
        ].forEach((stateName) => {
            node.classList.remove(`state-${stateName}`);
        });
    };

    const createSpeechMessage = (stateName, explicitMessage) => {
        const message = String(explicitMessage || "").trim();
        if (message) return message;
        return DEFAULT_MESSAGES[stateName] || "Rupy is ready.";
    };

    function setupFloatingRupyWidget() {
        const widgetNode = document.querySelector("[data-rupy-float]");
        if (!widgetNode) return;

        const bubbleNode = widgetNode.querySelector("[data-rupy-float-bubble]");
        const imageNode = widgetNode.querySelector("[data-rupy-float-image]");
        const toggleNode = widgetNode.querySelector("[data-rupy-float-toggle]");
        const fxNode = widgetNode.querySelector("[data-rupy-float-fx]");

        if (!imageNode) return;

        const pageKey = String(widgetNode.dataset.rupyPage || "").trim().toLowerCase();
        const imageMap = buildImageMap(widgetNode, imageNode);

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
            return imageMap[normalized] || imageMap.idle || "";
        };

        let activeState = "idle";
        let bubbleTimer = null;
        let moodTimer = null;
        let inactivityTimer = null;
        let tipsTimer = null;

        const clearTimer = (timerRef) => {
            if (!timerRef) return null;
            window.clearTimeout(timerRef);
            return null;
        };

        const clearIntervalTimer = (timerRef) => {
            if (!timerRef) return null;
            window.clearInterval(timerRef);
            return null;
        };

        const speak = (message, autoCollapseMs = 5200) => {
            if (!bubbleNode) return;
            const text = String(message || "").trim();
            if (!text) return;

            bubbleTimer = clearTimer(bubbleTimer);
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
            const normalized = normalizeState(nextState);
            activeState = normalized;

            removeStateClasses(widgetNode);
            widgetNode.classList.add(`state-${normalized}`);
            if (normalized === "celebration") widgetNode.classList.add("state-celebrate");
            if (normalized === "lazy-rich") widgetNode.classList.add("state-lazy");

            const nextImage = resolveStateImage(normalized);
            if (nextImage && String(imageNode.getAttribute("src") || "").trim() !== nextImage) {
                imageNode.setAttribute("src", nextImage);
            }

            const shouldSpeak = options.silent !== true;
            if (shouldSpeak) {
                const message = createSpeechMessage(normalized, options.message);
                if (message) speak(message, options.messageDurationMs);
            }

            if (options.burst || normalized === "celebration") {
                spawnBurstFx();
            }
            if (options.moneyRain || normalized === "money-rain") {
                spawnMoneyRainFx();
            }

            moodTimer = clearTimer(moodTimer);
            const holdMs = Number(options.holdMs || 0);
            if (holdMs > 0 && normalized !== "lazy-rich") {
                moodTimer = window.setTimeout(() => {
                    applyState("idle", { silent: true });
                }, holdMs);
            }
        };

        const resetInactivityTimer = () => {
            inactivityTimer = clearTimer(inactivityTimer);
            inactivityTimer = window.setTimeout(() => {
                applyState("lazy-rich", {
                    message: DEFAULT_MESSAGES["lazy-rich"],
                    holdMs: 4200,
                });
            }, INACTIVITY_TIMEOUT_MS);
        };

        const startRandomTips = () => {
            tipsTimer = clearIntervalTimer(tipsTimer);
            tipsTimer = window.setInterval(() => {
                if (document.hidden) return;
                const nextTip = RANDOM_TIPS[Math.floor(Math.random() * RANDOM_TIPS.length)];
                speak(nextTip, 4200);
            }, RANDOM_TIP_INTERVAL_MS);
        };

        const classifyToast = (toastType, rawMessage) => {
            const message = String(rawMessage || "").trim();
            const lowered = message.toLowerCase();
            const type = String(toastType || "info").trim().toLowerCase();

            if (lowered.includes("no spend day")) {
                return { state: "money-rain", message: message || "No Spend Day complete.", moneyRain: true, holdMs: 3600 };
            }
            if (lowered.includes("level") && lowered.includes("unlocked")) {
                return { state: "celebration", message: message || DEFAULT_MESSAGES.celebration, burst: true, holdMs: 3400 };
            }
            if (lowered.includes("streak")) {
                return { state: "notification", message: message || DEFAULT_MESSAGES.notification, holdMs: 3000 };
            }
            if (lowered.includes("goal") && (lowered.includes("complete") || lowered.includes("achiev"))) {
                return { state: "celebration", message: message || DEFAULT_MESSAGES.celebration, burst: true, holdMs: 3400 };
            }
            if (lowered.includes("warning") || lowered.includes("overspend") || lowered.includes("budget cross")) {
                return { state: "warning", message: message || DEFAULT_MESSAGES.warning, holdMs: 3400 };
            }
            if (lowered.includes("error") || type === "error") {
                return { state: "error", message: message || DEFAULT_MESSAGES.error, holdMs: 3400 };
            }
            if (type === "success") {
                return { state: "happy", message: message || DEFAULT_MESSAGES.happy, burst: true, holdMs: 2600 };
            }
            if (type === "warning") {
                return { state: "warning", message: message || DEFAULT_MESSAGES.warning, holdMs: 3000 };
            }
            return { state: "notification", message: message || DEFAULT_MESSAGES.notification, holdMs: 2400 };
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

        const handleRupyEvent = (eventType, payload = {}) => {
            const type = String(eventType || "").trim().toLowerCase();
            if (!type) return;

            if (type === "page_load") {
                applyState("hello", { message: String(payload.message || DEFAULT_MESSAGES.hello), holdMs: 1800 });
                return;
            }
            if (type === "login_success") {
                applyState("happy", { message: String(payload.message || DEFAULT_MESSAGES.hello), burst: true, holdMs: 2600 });
                return;
            }
            if (type === "expense_added") {
                applyState("happy", { message: String(payload.message || DEFAULT_MESSAGES.happy), burst: true, holdMs: 2200 });
                return;
            }
            if (type === "high_spending" || type === "overspending") {
                applyState("warning", { message: String(payload.message || DEFAULT_MESSAGES.warning), holdMs: 3600 });
                return;
            }
            if (type === "analytics_loading" || type === "loading") {
                applyState("loading", { message: String(payload.message || DEFAULT_MESSAGES.loading), holdMs: 2400 });
                return;
            }
            if (type === "budget_planning") {
                applyState("thinking", { message: String(payload.message || DEFAULT_MESSAGES.thinking), holdMs: 2800 });
                return;
            }
            if (type === "system_error" || type === "error") {
                applyState("error", { message: String(payload.message || DEFAULT_MESSAGES.error), holdMs: 3400 });
                return;
            }
            if (type === "level_up") {
                applyState("celebration", { message: String(payload.message || DEFAULT_MESSAGES.celebration), burst: true, holdMs: 3400 });
                return;
            }
            if (type === "streak_milestone") {
                applyState("notification", { message: String(payload.message || "Streak milestone unlocked."), holdMs: 3200 });
                return;
            }
            if (type === "no_spend_day") {
                applyState("money-rain", { message: String(payload.message || "No Spend Day complete."), moneyRain: true, holdMs: 3600 });
                return;
            }
            if (type === "achievement_unlocked") {
                applyState("celebration", { message: String(payload.message || DEFAULT_MESSAGES.celebration), burst: true, holdMs: 3400 });
                return;
            }
            if (type === "saving_money" || type === "budget_under_control") {
                applyState("money-rain", { message: String(payload.message || DEFAULT_MESSAGES.proud), moneyRain: true, holdMs: 3600 });
                return;
            }
            if (type === "notification" || type === "reminder" || type === "tip") {
                applyState("notification", { message: String(payload.message || DEFAULT_MESSAGES.notification), holdMs: 2200 });
                return;
            }
            if (type === "user_inactive") {
                applyState("lazy-rich", { message: String(payload.message || DEFAULT_MESSAGES["lazy-rich"]), holdMs: 4200 });
                return;
            }
            if (type === "idle") {
                applyState("idle", { message: String(payload.message || ""), holdMs: 0, silent: !payload.message });
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
                if (activeState === "lazy-rich") {
                    applyState("idle", { silent: true });
                }
                resetInactivityTimer();
            }, options);
        });

        const expenseForm = document.querySelector('form[action="/add"]');
        if (expenseForm) {
            expenseForm.addEventListener("submit", () => {
                handleRupyEvent("expense_added", {});
            });
        }

        window.addEventListener(RUPY_EVENT_NAME, (event) => {
            const detail = event?.detail || {};
            handleRupyEvent(detail.type, detail);
        });

        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                applyState("lazy-rich", { silent: true });
                return;
            }
            applyState("idle", { silent: true });
            resetInactivityTimer();
        });

        window.RupyMascot = {
            setState(stateName, options = {}) {
                const message = options && typeof options === "object" ? options.message : "";
                applyState(stateName, {
                    ...options,
                    message,
                });
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
            setMascotState(state, message = "") {
                applyState(state, {
                    message,
                });
            },
        };

        // Required global helper for direct usage: setMascotState("happy", "Nice! Expense added.")
        window.setMascotState = (state, message = "") => {
            window.RupyMascot.setMascotState(state, message);
        };

        watchToasts();

        // Page load -> hello, then fall back to idle.
        applyState("hello", { message: DEFAULT_MESSAGES.hello, holdMs: 1800 });
        if (pageKey === "dashboard") {
            window.setTimeout(() => {
                applyState("idle", { silent: true });
            }, 1900);
        }

        resetInactivityTimer();
        startRandomTips();
    }

    document.addEventListener("DOMContentLoaded", () => {
        setupFloatingRupyWidget();
    });
})();
