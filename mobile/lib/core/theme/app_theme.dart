import 'package:flutter/material.dart';

import 'app_colors.dart';

/// Le theme de l'application.
///
/// Un seul theme, clair. Le site force déjà `color-scheme: light` sur ses
/// champs de formulaire parce que le mode sombre automatique de certains
/// systemes inversait le fond sans inverser le texte, et rendait des
/// champs illisibles. Offrir ici un theme sombre a moitie teste
/// reproduirait ce defaut sur le téléphone ; mieux vaut un seul theme
/// juste qu'un second approximatif.
abstract final class AppTheme {
  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.brand600,
      brightness: Brightness.light,
    ).copyWith(
      primary: AppColors.brand600,
      onPrimary: Colors.white,
      secondary: AppColors.accent600,
      onSecondary: Colors.white,
      surface: AppColors.surface,
      onSurface: AppColors.foreground,
      error: AppColors.danger600,
      outline: AppColors.border,
    );

    const radius = 12.0;

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.background,
      splashFactory: InkSparkle.splashFactory,
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.background,
        foregroundColor: AppColors.foreground,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0.5,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: AppColors.foreground,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
      ),
      textTheme: const TextTheme(
        titleLarge: TextStyle(fontWeight: FontWeight.w700, color: AppColors.foreground),
        titleMedium: TextStyle(fontWeight: FontWeight.w600, color: AppColors.foreground),
        bodyMedium: TextStyle(color: AppColors.foreground, height: 1.4),
        bodySmall: TextStyle(color: AppColors.foregroundMuted, height: 1.4),
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.border,
        thickness: 1,
        space: 1,
      ),
      cardTheme: CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radius),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.brand600,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.brand200,
          disabledForegroundColor: Colors.white,
          minimumSize: const Size(0, 48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.brand700,
          minimumSize: const Size(0, 48),
          side: const BorderSide(color: AppColors.border),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: AppColors.brand700),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        // Chaque état declare son trait. Laisser Material choisir donnait
        // sur le site un champ dont la bordure disparaissait au focus.
        border: _border(AppColors.border),
        enabledBorder: _border(AppColors.border),
        focusedBorder: _border(AppColors.brand600, width: 2),
        errorBorder: _border(AppColors.danger600),
        focusedErrorBorder: _border(AppColors.danger600, width: 2),
        labelStyle: const TextStyle(color: AppColors.foregroundMuted),
        hintStyle: const TextStyle(color: AppColors.foregroundMuted),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surfaceMuted,
        side: const BorderSide(color: AppColors.border),
        labelStyle: const TextStyle(color: AppColors.foreground, fontSize: 13),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.brand800,
        contentTextStyle: const TextStyle(color: Colors.white),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.surface,
        indicatorColor: AppColors.brand100,
        surfaceTintColor: Colors.transparent,
        elevation: 3,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 12,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w600
                : FontWeight.w400,
            color: states.contains(WidgetState.selected)
                ? AppColors.brand800
                : AppColors.foregroundMuted,
          ),
        ),
      ),
    );
  }

  static OutlineInputBorder _border(Color color, {double width = 1}) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: BorderSide(color: color, width: width),
    );
  }
}
