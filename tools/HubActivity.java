package com.liskovsoft.smartyoutubetv2.tv.ui.main;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class HubActivity extends Activity {
    private static final int BG = Color.rgb(15, 15, 15);
    private static final int CARD = Color.rgb(34, 34, 34);
    private static final int CARD_FOCUSED = Color.rgb(61, 18, 18);
    private static final int ACCENT = Color.rgb(255, 65, 65);
    private long lastBackPress;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().getDecorView().setBackgroundColor(BG);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setPadding(dp(56), dp(32), dp(56), dp(32));
        root.setBackgroundColor(BG);

        TextView heading = new TextView(this);
        heading.setText("СМОТРЕТЬ");
        heading.setTextColor(Color.WHITE);
        heading.setTextSize(30);
        heading.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        heading.setGravity(Gravity.CENTER);
        root.addView(heading, new LinearLayout.LayoutParams(-1, -2));

        TextView subtitle = new TextView(this);
        subtitle.setText("Выбери приложение");
        subtitle.setTextColor(Color.LTGRAY);
        subtitle.setTextSize(16);
        subtitle.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams subtitleParams = new LinearLayout.LayoutParams(-1, -2);
        subtitleParams.topMargin = dp(8);
        subtitleParams.bottomMargin = dp(34);
        root.addView(subtitle, subtitleParams);

        LinearLayout cards = new LinearLayout(this);
        cards.setOrientation(LinearLayout.HORIZONTAL);
        cards.setGravity(Gravity.CENTER);
        root.addView(cards, new LinearLayout.LayoutParams(-1, -2));

        cards.addView(makeCard("YouTube", "YouTube, но лучше", ACCENT, () -> openSmartTube()), cardParams());
        cards.addView(makeCard("RuTube", "халявные фильмы", Color.rgb(255, 75, 55), () ->
                launchOrWeb(new String[]{"ru.rutube.app", "ru.rutube.tv"}, "https://rutube.ru/")), cardParams());
        cards.addView(makeCard("Кинопоиск", "не халяв", Color.rgb(255, 190, 45), () ->
                launchOrWeb(new String[]{"ru.kinopoisk"}, "https://hd.kinopoisk.ru/")), cardParams());
        cards.addView(makeCard("Аниксарт", "скоро", Color.rgb(120, 120, 160), () ->
                Toast.makeText(this, "Раздел пока не подключён", Toast.LENGTH_SHORT).show()), cardParams());

        setContentView(root);
        cards.getChildAt(0).requestFocus();
    }

    private LinearLayout makeCard(String title, String caption, int accent, Runnable action) {
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setGravity(Gravity.CENTER);
        content.setPadding(dp(12), dp(18), dp(12), dp(18));

        TextView name = new TextView(this);
        name.setText(title);
        name.setTextColor(Color.WHITE);
        name.setTextSize(22);
        name.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        name.setGravity(Gravity.CENTER);
        content.addView(name);

        TextView detail = new TextView(this);
        detail.setText(caption);
        detail.setTextColor(Color.LTGRAY);
        detail.setTextSize(14);
        detail.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams detailParams = new LinearLayout.LayoutParams(-1, -2);
        detailParams.topMargin = dp(10);
        content.addView(detail, detailParams);

        LinearLayout card = new LinearLayout(this);
        card.setFocusable(true);
        card.setClickable(true);
        card.setGravity(Gravity.CENTER);
        card.setBackground(cardBackground(CARD, accent));
        card.setOnFocusChangeListener((v, focused) ->
                card.setBackground(cardBackground(focused ? CARD_FOCUSED : CARD, accent)));
        card.setOnClickListener(v -> action.run());
        card.addView(content);
        return card;
    }

    private GradientDrawable cardBackground(int color, int accent) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(18));
        drawable.setStroke(dp(2), accent);
        return drawable;
    }

    private LinearLayout.LayoutParams cardParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(170), 1);
        params.setMargins(dp(9), 0, dp(9), 0);
        return params;
    }

    private void openSmartTube() {
        Intent intent = new Intent(this, SplashActivity.class);
        intent.setAction(Intent.ACTION_MAIN);
        startActivity(intent);
    }

    private void launchOrWeb(String[] packages, String url) {
        for (String packageName : packages) {
            Intent launch = getPackageManager().getLaunchIntentForPackage(packageName);
            if (launch != null) {
                startActivity(launch);
                return;
            }
        }
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (Exception e) {
            Toast.makeText(this, "Приложение не установлено", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    public void onBackPressed() {
        long now = System.currentTimeMillis();
        if (now - lastBackPress < 2000) {
            super.onBackPressed();
            return;
        }
        lastBackPress = now;
        Toast.makeText(this, "Нажми ещё раз, чтобы выйти", Toast.LENGTH_SHORT).show();
    }

    private int dp(float value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
