# ==========================================================
# City-level change table (wide) -> plots
# Expects columns like:
#   city, veg_patch_count_change, veg_patch_count_pct,
#   veg_mean_patch_area_m2_change, veg_mean_patch_area_m2_pct, ...
# Outputs:
#   out/spatial_changes_diverging_<IND>.png
#   out/spatial_changes_heatmap_pct.png
#   out/spatial_changes_lollipop_<IND>.png
# ==========================================================

pkgs <- c("readr","dplyr","tidyr","stringr","forcats","ggplot2","scales")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

dir.create("out", showWarnings = FALSE, recursive = TRUE)

# ---------- Load ----------
# Point this to your table (e.g., out/spatial_temporal_changes.csv)
path <- "out/spatial_temporal_changes.csv"

# Read robustly (treat "NA" as NA)
df <- readr::read_csv(path, na = c("NA",""), show_col_types = FALSE)

# If your column names are abbreviated like in the screenshot,
# you can rename them to friendlier forms here (optional):
# names(df)

# ---------- Coerce numerics ----------
num_cols <- setdiff(names(df), "city")
df <- df %>% mutate(across(all_of(num_cols), as.numeric))

# ---------- Helpers ----------
nice_label <- function(x) {
  x %>%
    str_replace("_pct$"," (%)") %>%
    str_replace_all("_"," ") %>%
    str_to_sentence()
}
theme_pub <- function() {
  theme_minimal(base_size = 12) +
    theme(panel.grid.minor = element_blank(),
          plot.title = element_text(face = "bold"),
          legend.position = "top")
}

# ==========================================================
# 1) Diverging bars for a chosen % change indicator
#    (pick any *_pct column that exists)
# ==========================================================
pct_candidates <- names(df)[str_detect(names(df), "_pct$")]
# Choose one to highlight (change here if you prefer another)
focus_pct <- pct_candidates[1]  # e.g., "veg_patch_count_pct"

if (!is.na(focus_pct)) {
  p_div <- df %>%
    mutate(city = fct_reorder(city, .data[[focus_pct]])) %>%
    ggplot(aes(x = city, y = .data[[focus_pct]], fill = .data[[focus_pct]] > 0)) +
    geom_col(width = 0.7) +
    geom_hline(yintercept = 0, linewidth = 0.6, color = "grey40") +
    coord_flip() +
    scale_fill_manual(values = c("#d73027","#1a9850"), guide = "none") +
    scale_y_continuous(labels = label_percent(scale = 1)) +
    labs(title = paste0(nice_label(focus_pct), " — change 2016→2024"),
         x = NULL, y = "% change") +
    theme_pub()
  ggsave(paste0("out/spatial_changes_diverging_", focus_pct, ".png"),
         p_div, width = 8, height = 5, dpi = 150)
}

# ==========================================================
# 2) Heatmap of all percent changes (cities × indicators)
# ==========================================================
if (length(pct_candidates)) {
  hm <- df %>%
    select(city, all_of(pct_candidates)) %>%
    pivot_longer(-city, names_to = "indicator", values_to = "pct") %>%
    mutate(indicator = nice_label(indicator))
  
  p_hm <- ggplot(hm, aes(x = indicator, y = city, fill = pct)) +
    geom_tile(color = "white", linewidth = 0.3) +
    scale_fill_gradient2(low = "#d73027", mid = "white", high = "#1a9850",
                         midpoint = 0, labels = label_percent(scale = 1)) +
    labs(title = "Percent change by indicator (2016→2024)",
         x = NULL, y = NULL, fill = "% change") +
    theme_pub() +
    theme(axis.text.x = element_text(angle = 30, hjust = 1))
  ggsave("out/spatial_changes_heatmap_pct.png", p_hm, width = 11, height = 6, dpi = 150)
}

# ==========================================================
# 3) Lollipop of absolute change for a chosen indicator
#    (pick any *_change column)
# ==========================================================
chg_candidates <- names(df)[str_detect(names(df), "_change$")]
focus_chg <- chg_candidates[1]  # e.g., "veg_patch_count_change"

if (!is.na(focus_chg)) {
  p_lolli <- df %>%
    mutate(city = fct_reorder(city, .data[[focus_chg]])) %>%
    ggplot(aes(y = city, x = .data[[focus_chg]],
               color = .data[[focus_chg]] > 0)) +
    geom_segment(aes(x = 0, xend = .data[[focus_chg]], y = city, yend = city),
                 linewidth = 0.7) +
    geom_point(size = 3) +
    scale_color_manual(values = c("#d73027","#1a9850"), guide = "none") +
    labs(title = paste0(nice_label(focus_chg), " — absolute change 2016→2024"),
         x = "Change", y = NULL) +
    theme_pub()
  ggsave(paste0("out/spatial_changes_lollipop_", focus_chg, ".png"),
         p_lolli, width = 8, height = 5, dpi = 150)
}

message("✅ Plots saved in 'out/'. You can switch 'focus_pct' / 'focus_chg' to other columns.")
