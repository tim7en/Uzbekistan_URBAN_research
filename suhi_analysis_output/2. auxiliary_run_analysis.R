# ==========================================================
# Comprehensive Analysis of Vegetation, Heat, and Biomass
# Dataset: stats_filled.csv (already filled)
# ==========================================================

# -------- Packages --------
pkgs <- c(
  "readr","dplyr","tidyr","ggplot2",
  "broom","scales","forcats","ggcorrplot"
)
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# -------- Load data --------
df <- read_csv("out/stats_filled.csv")

# Check structure
glimpse(df)


clean_outliers <- function(x) {
  # remove impossible values (< -1 or > 1 are invalid for vegetation indices)
  x[x < -1 | x > 1] <- NA
  return(x)
}

df <- df %>%
  mutate(
    summer_evi_mean  = clean_outliers(summer_evi_mean),
    winter_evi_mean  = clean_outliers(winter_evi_mean),
    evi_change_mean  = clean_outliers(evi_change_mean)
  )

# Optionally: drop rows with NA after cleaning
# df <- df %>% drop_na(summer_evi_mean, winter_evi_mean, evi_change_mean)

# Or: interpolate missing values (since your file is already "filled")
df <- df %>%
  group_by(city) %>%
  arrange(year, .by_group = TRUE) %>%
  mutate(
    summer_evi_mean = zoo::na.approx(summer_evi_mean, na.rm = FALSE),
    winter_evi_mean = zoo::na.approx(winter_evi_mean, na.rm = FALSE),
    evi_change_mean = zoo::na.approx(evi_change_mean, na.rm = FALSE)
  ) %>%
  ungroup()



# -------- Summary stats --------
summary_stats <- df %>%
  group_by(city) %>%
  summarise(across(where(is.numeric), list(mean = mean, sd = sd), .names = "{.col}_{.fn}"))

write_csv(summary_stats, "out/summary_stats.csv")

# -------- Trend analysis (linear regression by city) --------
trend_models <- df %>%
  group_by(city) %>%
  do({
    mod <- lm(summer_ndvi_mean ~ year, data = .)
    tidy(mod)
  })

write_csv(trend_models, "out/ndvi_trends.csv")

# -------- Correlation analysis --------
cor_vars <- c("summer_ndvi_mean","winter_ndvi_mean","ndvi_change_mean",
              "summer_evi_mean","winter_evi_mean","evi_change_mean",
              "summer_lst_mean","winter_lst_mean","lst_change_mean",
              "summer_biomass_t_per_ha","winter_biomass_t_per_ha","biomass_change_t_per_ha")

cor_matrix <- cor(df[cor_vars], use = "pairwise.complete.obs")

png("out/correlation_heatmap.png", width = 900, height = 700)
ggcorrplot(cor_matrix, hc.order = TRUE, type = "lower",
           lab = TRUE, lab_size = 3, colors = c("blue","white","red")) +
  ggtitle("Correlation Heatmap: Vegetation, LST, Biomass")
dev.off()

# -------- Time series plots by city --------
plot_vars <- c("summer_ndvi_mean","summer_evi_mean","summer_lst_mean","summer_biomass_t_per_ha")

for (v in plot_vars) {
  p <- ggplot(df, aes(x = year, y = .data[[v]], color = city, group = city)) +
    geom_line(size = 1) + geom_point() +
    theme_minimal() +
    labs(title = paste("Trend of", v, "by City"),
         y = v, x = "Year")
  
  ggsave(filename = paste0("out/", v, "_trend.png"), plot = p, width = 10, height = 6)
}

# -------- Change distributions --------
change_vars <- c("ndvi_change_mean","evi_change_mean","lst_change_mean","biomass_change_t_per_ha")

for (v in change_vars) {
  p <- ggplot(df, aes(x = city, y = .data[[v]], fill = city)) +
    geom_boxplot() +
    theme_minimal() +
    coord_flip() +
    labs(title = paste("Distribution of", v, "across Cities"),
         y = v, x = "City")
  
  ggsave(filename = paste0("out/", v, "_distribution.png"), plot = p, width = 9, height = 6)
}

message("Analysis complete. Outputs saved in 'out/' folder.")
