(() => {
    "use strict";

    if (window.__RUPY_ENGINE_READY__) return;
    window.__RUPY_ENGINE_READY__ = true;

    const EVENT_NAME = "rupy:event";
    const DEFAULT_ASSET_BASE = "/static/mascot/rupy/";
    const INACTIVITY_MS = 30000;

    const statesApi = window.RupyMascotStates;
    const uiApi = window.RupyMascotUI;

    if (!statesApi || !uiApi) {
        console.warn("RupyEngine not initialized: states/ui module missing.");
        return;
    }

    const toDatasetKey = (stateName) => {
        const normalized = String(stateName || "").trim().toLowerCase();
        const segments = normalized.split("-");
        return segments
            .map((segment, index) => index === 0 ? segment : `${segment.charAt(0).toUpperCase()}${segment.slice(1)}`)
            .join("");
    };

    const parseNumeric = (rawValue, fallbackValue = 0) => {
        const normalized = String(rawValue ?? "").replaceAll(",", "").trim();
        const value = Number(normalized);
        return Number.isFinite(value) ? value : fallbackValue;
    };

    const classifyToastReaction = (type, rawMessage = "") => {
        const toastType = String(type || "info").trim().toLowerCase();
        const message = String(rawMessage || "").trim();
        const lowered = message.toLowerCase();

        if (lowered.includes("goal") && (lowered.includes("achiev") || lowered.includes("complete"))) {
            return { state: "celebration", message };
        }
        if (lowered.includes("streak")) {
            return { state: "proud", message };
        }
        if (lowered.includes("coffee")) {
            return { state: "coffee-spend", message };
        }
        if (lowered.includes("overspend") || lowered.includes("budget") || lowered.includes("warning")) {
            return { state: "warning", message };
        }
        if (toastType === "error" || lowered.includes("error") || lowered.includes("failed")) {
            return { state: "error", message };
        }
        if (toastType === "success") {
            return { state: "happy", message };
        }
        if (toastType === "warning") {
            return { state: "warning", message };
        }
        return { state: "notification", message };
    };

    const createImageResolver = (rootNode) => {
        const explicitBase = String(rootNode.dataset.rupyAssetBase || "").trim();
        const base = explicitBase ? (explicitBase.endsWith("/") ? explicitBase : `${explicitBase}/`) : DEFAULT_ASSET_BASE;

        const resolve = (stateName) => {
            const normalized = statesApi.normalizeState(stateName);
            const datasetKey = `rupyImg${toDatasetKey(normalized).charAt(0).toUpperCase()}${toDatasetKey(normalized).slice(1)}`;
            const override = String(rootNode.dataset[datasetKey] || "").trim();
            if (override) return override;

            const assetFile = statesApi.stateAssets[normalized];
            if (!assetFile) return "";
            return `${base}${assetFile}`;
        };

        return { resolve };
    };

    function createEngine(rootNode) {
        const stateNames = statesApi.listStates();
        const ui = uiApi.create(rootNode, {
            storageKey: "expensepro-rupy-position-v1",
            stateNames,
        });
        if (!ui) return null;

        const imageResolver = createImageResolver(rootNode);
        const imageCache = new Map();

        let activeState = "idle";
        let lastTransientTimer = null;
        let inactivityTimer = null;
        let hoverCooldownTimer = null;
        let transitionToken = 0;

        const clearTransientTimer = () => {
            if (!lastTransientTimer) return;
            window.clearTimeout(lastTransientTimer);
            lastTransientTimer = null;
        };

        const clearInactivityTimer = () => {
            if (!inactivityTimer) return;
            window.clearTimeout(inactivityTimer);
            inactivityTimer = null;
        };

        const preloadState = (stateName) => {
            const src = imageResolver.resolve(stateName);
            if (!src) return Promise.resolve("");
            if (imageCache.has(src)) return imageCache.get(src);

            const promise = new Promise((resolve) => {
                const image = new Image();
                image.decoding = "async";
                image.loading = "lazy";
                image.onload = () => resolve(src);
                image.onerror = () => resolve(src);
                image.src = src;
            });
            imageCache.set(src, promise);
            return promise;
        };

        const animationForState = (stateName, explicitAnimation = "") => {
            const explicit = String(explicitAnimation || "").trim();
            if (explicit) return explicit;

            if (stateName === "warning" || stateName === "error" || stateName === "angry") return "shake";
            if (stateName === "celebration" || stateName === "money-rain") return "jump";
            if (stateName === "notification" || stateName === "lightbulb-idea") return "pop";
            if (stateName === "happy" || stateName === "proud" || stateName === "thumbs-up" || stateName === "wink") return "wiggle";
            if (stateName === "thinking" || stateName === "loading" || stateName === "analyzing-chart") return "bounce";
            return "";
        };

        const scheduleIdleFallback = (delayMs) => {
            const safeDelay = Number(delayMs);
            if (!Number.isFinite(safeDelay) || safeDelay <= 0) return;
            clearTransientTimer();
            lastTransientTimer = window.setTimeout(() => {
                void show("idle", "", { silent: true });
            }, safeDelay);
        };

        const restartInactivityWatch = () => {
            clearInactivityTimer();
            inactivityTimer = window.setTimeout(() => {
                const idleState = statesApi.pickIdleState();
                const idleMessage = statesApi.messageForState(idleState);
                void show(idleState, idleMessage, {
                    autoIdleAfterMs: 2600,
                });
            }, INACTIVITY_MS);
        };

        const show = async (rawState, message = "", options = {}) => {
            const normalized = statesApi.normalizeState(rawState);
            const token = ++transitionToken;

            const src = imageResolver.resolve(normalized);
            if (src) {
                await preloadState(normalized);
                if (token !== transitionToken) return false;
                ui.setImage(src);
            }

            ui.setState(normalized, {
                animation: animationForState(normalized, options.animation),
            });
            activeState = normalized;

            const shouldSpeak = options.silent !== true;
            if (shouldSpeak) {
                const finalMessage = statesApi.messageForState(normalized, message || options.message || "");
                if (finalMessage) {
                    ui.speak(finalMessage, Number(options.durationMs) || 4200);
                }
            }

            if (options.autoIdleAfterMs) {
                scheduleIdleFallback(Number(options.autoIdleAfterMs));
            }
            return true;
        };

        const emit = (type, payload = {}) => {
            window.dispatchEvent(new CustomEvent(EVENT_NAME, {
                detail: {
                    type,
                    ...payload,
                },
            }));
        };

        const handleEvent = async (type, payload = {}) => {
            const eventType = String(type || "").trim().toLowerCase();
            if (!eventType) return;

            const mappedState = statesApi.stateForEvent(eventType);
            const message = String(payload.message || payload.text || "").trim();

            if (eventType === "page_load") {
                await show("hello", message, { autoIdleAfterMs: 2100 });
                return;
            }
            if (eventType === "user_inactive") {
                await show(statesApi.pickIdleState(), message, { autoIdleAfterMs: 2400 });
                return;
            }
            if (eventType === "goal_achieved" || eventType === "goal_completed") {
                await show("celebration", message, { autoIdleAfterMs: 3200 });
                return;
            }
            if (eventType === "expense_added") {
                await show("thumbs-up", message, { autoIdleAfterMs: 2200 });
                return;
            }
            if (eventType === "budget_exceeded" || eventType === "overspending" || eventType === "high_spending") {
                await show("warning", message, { autoIdleAfterMs: 3400 });
                return;
            }
            if (eventType === "saving_streak" || eventType === "streak_milestone") {
                await show("proud", message, { autoIdleAfterMs: 2800 });
                return;
            }
            await show(mappedState, message, { autoIdleAfterMs: 2600 });
        };

        const bindIdleWatch = () => {
            const activityHandler = () => {
                restartInactivityWatch();
                if (activeState === "lazy-rich" || activeState === "thinking" || activeState === "sunglasses") {
                    void show("idle", "", { silent: true });
                }
            };

            const passive = { passive: true };
            document.addEventListener("pointerdown", activityHandler, passive);
            document.addEventListener("touchstart", activityHandler, passive);
            document.addEventListener("scroll", activityHandler, passive);
            document.addEventListener("mousemove", activityHandler, passive);
            document.addEventListener("keydown", activityHandler);
        };

        const bindHoverReaction = () => {
            ui.onHover(() => {
                if (hoverCooldownTimer) return;
                if (activeState === "warning" || activeState === "error" || activeState === "loading") return;
                hoverCooldownTimer = window.setTimeout(() => {
                    hoverCooldownTimer = null;
                }, 1500);
                void show("wink", "", {
                    silent: true,
                    animation: "wiggle",
                    autoIdleAfterMs: 900,
                });
            });
        };

        const bindToastObserver = () => {
            const toastContainer = document.querySelector("[data-toast-container]");
            if (!toastContainer) return;

            const readType = (toastNode) => {
                if (toastNode.classList.contains("toast-error")) return "error";
                if (toastNode.classList.contains("toast-warning")) return "warning";
                if (toastNode.classList.contains("toast-success")) return "success";
                return "info";
            };

            const reactToToast = (toastNode) => {
                if (!toastNode || toastNode.dataset.rupyObserved === "1") return;
                toastNode.dataset.rupyObserved = "1";
                const copyNode = toastNode.querySelector(".toast-copy");
                const copyText = copyNode ? String(copyNode.textContent || "").trim() : "";
                const reaction = classifyToastReaction(readType(toastNode), copyText);
                void show(reaction.state, reaction.message, { autoIdleAfterMs: 3000 });
            };

            toastContainer.querySelectorAll(".toast").forEach((node) => reactToToast(node));

            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (!(node instanceof HTMLElement)) return;
                        if (node.matches(".toast")) {
                            reactToToast(node);
                            return;
                        }
                        const nestedToast = node.querySelector(".toast");
                        if (nestedToast) reactToToast(nestedToast);
                    });
                });
            });
            observer.observe(toastContainer, { childList: true, subtree: true });
        };

        const api = {
            show(stateName, message = "", options = {}) {
                return show(stateName, message, options);
            },
            warn(message = "Overspending detected") {
                return show("warning", message, { autoIdleAfterMs: 3400 });
            },
            celebrate(message = "Milestone achieved!") {
                return show("celebration", message, { autoIdleAfterMs: 3200 });
            },
            tip(message = "Track your expenses daily.") {
                return show("notification", message, { autoIdleAfterMs: 2800 });
            },
            notify(message = "New update from Rupy.") {
                return show("notification", message, { autoIdleAfterMs: 2800 });
            },
            loading(message = "Loading your finance insights...") {
                return show("loading", message, { autoIdleAfterMs: 2600 });
            },
            error(message = "Something went wrong. Please try again.") {
                return show("error", message, { autoIdleAfterMs: 3200 });
            },
            emit,
            onExpenseAdded(payload = {}) {
                const category = String(payload.category || "").trim();
                const amount = Number(payload.amount);
                const amountLabel = Number.isFinite(amount) ? `Rs ${amount}` : "expense";
                const message = category
                    ? `Expense added: ${amountLabel} on ${category}.`
                    : "Expense added successfully.";
                return show("thumbs-up", message, { autoIdleAfterMs: 2300 });
            },
            onBudgetExceeded(payload = {}) {
                const amount = Number(payload.amount);
                const amountLabel = Number.isFinite(amount) ? `Rs ${amount}` : "your limit";
                return show("warning", `Budget alert: you crossed ${amountLabel}.`, { autoIdleAfterMs: 3600 });
            },
            onGoalAchieved(payload = {}) {
                const title = String(payload.title || "Goal").trim();
                return show("celebration", `${title} achieved!`, { autoIdleAfterMs: 3200 });
            },
            onSavingStreak(payload = {}) {
                const days = Number(payload.days);
                const dayLabel = Number.isFinite(days) && days > 0 ? `${days} day streak` : "saving streak";
                return show("proud", `${dayLabel} active. Keep it going.`, { autoIdleAfterMs: 3000 });
            },
            onNoExpenses() {
                return show("confused", "No expenses logged yet. Add one now.", { autoIdleAfterMs: 2800 });
            },
            getState() {
                return activeState;
            },
            preloadState,
            resetPosition() {
                ui.resetPosition();
            },
        };

        bindIdleWatch();
        bindHoverReaction();
        bindToastObserver();

        window.addEventListener(EVENT_NAME, (event) => {
            const detail = event?.detail || {};
            void handleEvent(detail.type, detail);
        });

        document.addEventListener("visibilitychange", () => {
            if (document.hidden) return;
            restartInactivityWatch();
        });

        const initialState = statesApi.inferInitialState({
            page: rootNode.dataset.rupyPage || "",
            budgetLeft: parseNumeric(rootNode.dataset.rupyBudgetLeft, NaN),
            spentPercent: parseNumeric(rootNode.dataset.rupySpentPercent, NaN),
        });
        void show(initialState, statesApi.messageForState(initialState), {
            autoIdleAfterMs: initialState === "hello" || initialState === "login" ? 2200 : 0,
        });

        restartInactivityWatch();

        return api;
    }

    document.addEventListener("DOMContentLoaded", () => {
        const rootNode = document.querySelector("[data-rupy-float]");
        if (!rootNode) return;

        const engine = createEngine(rootNode);
        if (!engine) return;

        window.RupyEngine = engine;

        // Backward compatibility with existing app events.
        window.RupyMascot = {
            setState(stateName, options = {}) {
                const message = String(options?.message || "").trim();
                return engine.show(stateName, message, options);
            },
            speak(message, autoCollapseMs = 4200) {
                return engine.tip(String(message || "").trim(), {
                    durationMs: autoCollapseMs,
                });
            },
            emit(type, payload = {}) {
                return engine.emit(type, payload);
            },
            setMascotState(stateName, message = "") {
                return engine.show(stateName, message);
            },
        };

        window.setMascotState = (stateName, message = "") => {
            engine.show(stateName, message);
        };

        // Short-hand API for product teams using `Rupy.show(...)`.
        window.Rupy = {
            show(stateName, message = "", options = {}) {
                return engine.show(stateName, message, options);
            },
            warn(message = "Overspending detected") {
                return engine.warn(message);
            },
            celebrate(message = "Milestone achieved!") {
                return engine.celebrate(message);
            },
            tip(message = "Track your expenses daily.") {
                return engine.tip(message);
            },
        };
    });
})();
