# ==============================
# SUHI charts: 2016 vs 2024 (+ dashboard-style chart)
# Works with columns: suhi_day / suhi_night (from your new JSON)
# ==============================

# ---- Packages ----
pkgs <- c("readr","dplyr","tidyr","ggplot2","forcats","stringr","scales","broom")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Input ----
data_path <- "out/suhi_batch_summary_flat.csv"   # <- change if needed

# ---- Read ----
df_raw <- readr::read_csv(data_path, show_col_types = FALSE)

# ==============================
# Data Preparation
# ==============================
num <- function(x) suppressWarnings(as.numeric(x))
safe_se_from_ci <- function(lo, hi) num((hi - lo) / (2 * 1.96))

df_suhi <- df_raw %>%
  mutate(
    city = as.character(city),
    year = as.integer(year),
    
    # Calculate standard errors
    se_u_day   = coalesce(num(day_urban_stderr),
                         safe_se_from_ci(day_urban_ci95_lo, day_urban_ci95_hi)),
    se_r_day   = coalesce(num(day_rural_stderr),
                         safe_se_from_ci(day_rural_ci95_lo, day_rural_ci95_hi)),
    se_day     = sqrt(se_u_day^2 + se_r_day^2),
    
    se_u_night = coalesce(num(night_urban_stderr),
                         safe_se_from_ci(night_urban_ci95_lo, night_urban_ci95_hi)),
    se_r_night = coalesce(num(night_rural_stderr),
                         safe_se_from_ci(night_rural_ci95_lo, night_rural_ci95_hi)),
    se_night   = sqrt(se_u_night^2 + se_r_night^2),
    
    # Calculate SUHI values and CIs
    suhi_day   = num(suhi_day),
    suhi_night = num(suhi_night),
    suhi_day_lo   = suhi_day - 1.96 * se_day,
    suhi_day_hi   = suhi_day + 1.96 * se_day,
    suhi_night_lo = suhi_night - 1.96 * se_night,
    suhi_night_hi = suhi_night + 1.96 * se_night
  ) %>%
  select(city, year, matches("suhi_|se_"))

# Create long format data
suhi_long <- df_suhi %>%
  pivot_longer(
    matches("suhi_|se_"),
    names_to = "key",
    values_to = "val"
  ) %>%
  mutate(
    metric = case_when(
      str_detect(key, "day") ~ "Day",
      str_detect(key, "night") ~ "Night"
    ),
    stat = case_when(
      str_detect(key, "_lo$") ~ "lo",
      str_detect(key, "_hi$") ~ "hi",
      str_detect(key, "^se_") ~ "se",
      TRUE ~ "mean"
    )
  ) %>%
  select(-key) %>%
  pivot_wider(names_from = stat, values_from = val) %>%
  mutate(
    lo = coalesce(lo, mean - 1.96 * se),
    hi = coalesce(hi, mean + 1.96 * se)
  ) %>%
  rename(suhi = mean)

# Filter to comparison years
suhi_2yrs <- suhi_long %>% filter(year %in% c(2016, 2024))

# ==============================
# Change Calculation
# ==============================
chg <- suhi_2yrs %>%
  select(city, metric, year, suhi, se) %>%
  pivot_wider(names_from = year, 
              values_from = c(suhi, se), 
              names_prefix = "Y") %>%
  mutate(
    change = suhi_Y2024 - suhi_Y2016,
    se_change = sqrt(se_Y2024^2 + se_Y2016^2),
    lo_change = change - 1.96 * se_change,
    hi_change = change + 1.96 * se_change
  )

# Create city ordering
city_levels <- chg %>%
  group_by(city) %>%
  summarise(order_val = mean(change, na.rm = TRUE)) %>%
  arrange(order_val) %>%
  pull(city)

# ==============================
# Plotting Functions
# ==============================
create_plot_dir <- function() {
  if (!dir.exists("plots")) dir.create("plots", recursive = TRUE)
}

# ==============================
# Plot A: SUHI Change
# ==============================
create_plot_dir()
pd <- position_dodge(width = 0.75)

p_change <- ggplot(chg, aes(x = factor(city, levels = city_levels), y = change, fill = metric)) +
  geom_col(position = pd, width = 0.7) +
  geom_errorbar(aes(ymin = lo_change, ymax = hi_change), position = pd, width = 0.25) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  coord_flip() +
  labs(
    title = "ΔSUHI (2024 − 2016) by city with 95% CI",
    subtitle = "Bars show SUHI change; error bars are 95% CIs",
    x = "City",
    y = "Change in SUHI (°C)",
    fill = "Metric"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "top")

ggsave("plots/06_delta_suhi_2024_minus_2016_by_city_with_CI.png",
       p_change, width = 12, height = 8, dpi = 300)

# ==============================
# Plots B1 & B2: SUHI Levels
# ==============================
plot_levels <- function(metric_type) {
  df_plot <- suhi_2yrs %>%
    filter(metric == metric_type) %>%
    mutate(city_f = factor(city, levels = city_levels))
  
  ggplot(df_plot, aes(x = city_f, y = suhi, fill = factor(year))) +
    geom_col(position = pd, width = 0.7) +
    geom_errorbar(aes(ymin = lo, ymax = hi), position = pd, width = 0.25) +
    coord_flip() +
    geom_hline(yintercept = 0, linetype = "dashed") +
    labs(
      title = paste("SUHI levels by city (2016 vs 2024) —", metric_type),
      subtitle = "Bars = mean SUHI; whiskers = 95% CI",
      x = "City",
      y = paste0(metric_type, "time SUHI (°C)"),
      fill = "Year"
    ) +
    theme_minimal(base_size = 12) +
    theme(legend.position = "top")
}

walk(c("Day", "Night"), ~{
  ggsave(paste0("plots/07_suhi_levels_", .x, "_2016_vs_2024.png"),
         plot_levels(.x), width = 12, height = 9, dpi = 300)
})

# ==============================
# Trend Analysis (2016-2024)
# ==============================
df_trend <- suhi_long %>% filter(between(year, 2016, 2024))

trend_stats <- df_trend %>%
  group_by(city, metric) %>%
  do({
    fit <- lm(suhi ~ year, data = .)
    tidy(fit) %>%
      filter(term == "year") %>%
      select(p.value)
  }) %>%
  ungroup() %>%
  mutate(
    stars = case_when(
      p.value < 0.001 ~ "***",
      p.value < 0.01 ~ "**",
      p.value < 0.05 ~ "*",
      TRUE ~ "ns"
    )
  )

# Create trend plot with p-values
p_trend <- df_trend %>%
  ggplot(aes(x = year, y = suhi, color = metric)) +
  geom_ribbon(aes(ymin = lo, ymax = hi, fill = metric), alpha = 0.2) +
  geom_line() +
  geom_point() +
  facet_wrap(~city, scales = "free_y") +
  geom_text(
    data = trend_stats,
    aes(x = 2022, y = Inf, label = paste("p =", round(p.value, 3), stars)),
    vjust = 1.5, size = 3, color = "black"
  ) +
  labs(
    title = "SUHI Trends (2016-2024) with 95% CI",
    x = "Year",
    y = "SUHI (°C)"
  ) +
  theme_minimal()

ggsave("plots/08_suhi_trends.png", p_trend, width = 14, height = 10, dpi = 300)