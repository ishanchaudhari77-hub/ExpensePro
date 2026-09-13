(() => {
    "use strict";

    if (window.RupyMascotStates) return;

    const STATE_ASSET_MAP = Object.freeze({
        idle: "rupy_idle.png",
        hello: "rupy_hello.png",
        login: "rupy_login.png",
        happy: "rupy_happy.png",
        "thumbs-up": "rupy_thumbs_up.png",
        thinking: "rupy_thinking.png",
        confused: "rupy_confused.png",
        warning: "rupy_warning.png",
        error: "rupy_error.png",
        celebration: "rupy_celebration.png",
        "lazy-rich": "rupy_lazy_rich.png",
        proud: "rupy_proud.png",
        broke: "rupy_broke.png",
        notification: "rupy_notification.png",
        loading: "rupy_loading.png",
        wink: "rupy_wink.png",
        sunglasses: "rupy_sunglasses.png",
        angry: "rupy_angry.png",
        sad: "rupy_sad.png",
        shocked: "rupy_shocked.png",
        "coffee-spend": "rupy_coffee_spend.png",
        "analyzing-chart": "rupy_analyzing_chart.png",
        "lightbulb-idea": "rupy_lightbulb_idea.png",
        "money-rain": "rupy_money_rain.png",
    });

    const STATE_ALIASES = Object.freeze({
        success: "happy",
        celebrate: "celebration",
        celebratory: "celebration",
        lazy: "lazy-rich",
        sleep: "lazy-rich",
        rich: "lazy-rich",
        thumbs_up: "thumbs-up",
        thumbsup: "thumbs-up",
        no_expenses: "confused",
        overspending: "warning",
        budget_exceeded: "warning",
        alert: "warning",
        idea: "lightbulb-idea",
        analyzing: "analyzing-chart",
        chart: "analyzing-chart",
        notify: "notification",
        money_rain: "money-rain",
        moneyrain: "money-rain",
    });

    const EVENT_STATE_MAP = Object.freeze({
        page_load: "hello",
        login_success: "login",
        login: "login",
        expense_added: "thumbs-up",
        high_spending: "warning",
        overspending: "warning",
        budget_exceeded: "warning",
        budget_under_control: "proud",
        saving_streak: "proud",
        streak_milestone: "proud",
        goal_achieved: "celebration",
        goal_completed: "celebration",
        achievement_unlocked: "celebration",
        no_spend_day: "money-rain",
        no_expenses: "confused",
        user_inactive: "lazy-rich",
        analytics_loading: "loading",
        loading: "loading",
        tip: "notification",
        reminder: "notification",
        notification: "notification",
        budget_planning: "thinking",
        system_error: "error",
        error: "error",
    });

    const DEFAULT_MESSAGES = Object.freeze({
        idle: "Ready when you are.",
        hello: "Welcome back! Ready to track money?",
        login: "Welcome back! Let's control your money.",
        happy: "Nice! Smart money move.",
        "thumbs-up": "Great! Expense tracked.",
        thinking: "Give me a sec, analyzing your spending.",
        confused: "No expenses yet. Add one to get insights.",
        warning: "Careful, budget pressure is building.",
        error: "Something broke. Let's retry.",
        celebration: "Goal achieved! Big win.",
        "lazy-rich": "No activity for a while. Quick money check?",
        proud: "Strong streak. Keep this discipline.",
        broke: "This pattern can hurt savings. Reset today.",
        notification: "Quick update from Rupy.",
        loading: "Crunching your finance data...",
        wink: "Got your attention.",
        sunglasses: "Looks smooth. Keep tracking daily.",
        "coffee-spend": "Coffee spending is climbing today.",
        "analyzing-chart": "Chart check done. Want category insights?",
        "lightbulb-idea": "Idea: set a cap for your top category.",
        "money-rain": "No-spend discipline unlocked.",
    });

    const IDLE_STATES = Object.freeze(["thinking", "lazy-rich", "sunglasses"]);

    const normalizeState = (rawState) => {
        const normalized = String(rawState || "").trim().toLowerCase().replace(/\s+/g, "-");
        if (!normalized) return "idle";
        if (STATE_ALIASES[normalized]) return STATE_ALIASES[normalized];
        if (STATE_ASSET_MAP[normalized]) return normalized;
        return "idle";
    };

    const stateForEvent = (rawEventType) => {
        const normalized = String(rawEventType || "").trim().toLowerCase();
        if (!normalized) return "idle";
        return normalizeState(EVENT_STATE_MAP[normalized] || normalized);
    };

    const messageForState = (state, fallbackMessage = "") => {
        const explicit = String(fallbackMessage || "").trim();
        if (explicit) return explicit;
        const normalized = normalizeState(state);
        return DEFAULT_MESSAGES[normalized] || DEFAULT_MESSAGES.idle;
    };

    const inferInitialState = (context = {}) => {
        const page = String(context.page || "").trim().toLowerCase();
        const budgetLeft = Number(context.budgetLeft);
        const spentPercent = Number(context.spentPercent);
        const hasExpenses = context.hasExpenses;

        if (page.includes("login") || page.includes("register")) {
            return "login";
        }
        if (Number.isFinite(spentPercent) && spentPercent >= 100) {
            return "warning";
        }
        if (Number.isFinite(budgetLeft) && budgetLeft < 0) {
            return "warning";
        }
        if (hasExpenses === false) {
            return "confused";
        }
        if (Number.isFinite(spentPercent) && spentPercent === 0 && Number.isFinite(budgetLeft) && budgetLeft > 0) {
            return "confused";
        }
        return "hello";
    };

    const pickIdleState = () => {
        const index = Math.floor(Math.random() * IDLE_STATES.length);
        return IDLE_STATES[index] || "thinking";
    };

    const listStates = () => Object.keys(STATE_ASSET_MAP);

    window.RupyMascotStates = Object.freeze({
        stateAssets: STATE_ASSET_MAP,
        eventStateMap: EVENT_STATE_MAP,
        defaultMessages: DEFAULT_MESSAGES,
        idleStates: IDLE_STATES,
        normalizeState,
        stateForEvent,
        messageForState,
        inferInitialState,
        pickIdleState,
        listStates,
    });
})();
