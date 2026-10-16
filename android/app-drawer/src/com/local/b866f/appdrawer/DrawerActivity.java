package com.local.b866f.appdrawer;

import android.app.Activity;
import android.app.AlertDialog;
import android.animation.ValueAnimator;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ImageDecoder;
import android.graphics.Rect;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextWatcher;
import android.text.TextUtils;
import android.util.LruCache;
import android.util.AtomicFile;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.view.animation.DecelerateInterpolator;
import android.widget.BaseAdapter;
import android.widget.EditText;
import android.widget.GridView;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.text.Collator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Foreground-only TV app drawer. No Home role, root, accessibility or network access. */
public final class DrawerActivity extends Activity {
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService loader = Executors.newSingleThreadExecutor();
    private final ExecutorService images = Executors.newFixedThreadPool(2);
    private final LruCache<String, Bitmap> cache = new LruCache<String, Bitmap>(6 * 1024 * 1024) {
        @Override protected int sizeOf(String k, Bitmap b) { return b.getByteCount(); }
    };
    private final List<Entry> all = new ArrayList<>(), visible = new ArrayList<>();
    private SharedPreferences prefs;
    private Set<String> favorites, hidden;
    private GridView grid;
    private TextView status, filterButton, sortButton;
    private EditText search;
    private final AppsAdapter adapter = new AppsAdapter();
    private boolean favoritesOnly, banners, registered, importingWallpaper;
    private volatile boolean closed;
    private volatile int wallpaperGeneration;
    private Bitmap wallpaperBitmap;
    private ImageView wallpaperView;
    private View wallpaperShade;
    private static final int PICK_WALLPAPER = 41;
    private int sort, columns, loadGeneration;
    private String query = "";
    private int bg, surface, text, muted, accent;
    private String restoreKey;
    private final BroadcastReceiver packages = new BroadcastReceiver() {
        @Override public void onReceive(Context c, Intent i) { cache.evictAll(); loadApps(); }
    };

    private static final class Entry {
        final ComponentName component;
        final String key, label;
        Entry(ResolveInfo ri, PackageManager pm) {
            component = new ComponentName(ri.activityInfo.packageName, ri.activityInfo.name);
            key = component.flattenToString();
            CharSequence l = ri.loadLabel(pm);
            label = l == null ? component.getPackageName() : l.toString();
        }
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("drawer", MODE_PRIVATE);
        if (!prefs.contains("wallpaperEnabled")) prefs.edit().putBoolean("wallpaperEnabled", wallpaperFile().exists()).apply();
        favorites = new HashSet<>(prefs.getStringSet("favorites", Collections.<String>emptySet()));
        hidden = new HashSet<>(prefs.getStringSet("hidden", Collections.<String>emptySet()));
        if (!prefs.getBoolean("compactTiles", false)) {
            prefs.edit().putInt("columns", 7).putBoolean("compactTiles", true).apply();
        }
        columns = Math.max(5, Math.min(7, prefs.getInt("columns", 7)));
        sort = Math.max(0, Math.min(2, prefs.getInt("sort", 0)));
        banners = prefs.getBoolean("banners", true);
        if (state != null) {
            query = state.getString("query", "");
            favoritesOnly = state.getBoolean("favoritesOnly");
            restoreKey = state.getString("selected");
        }
        buildUi();
        loadWallpaper();
    }

    @Override public void onStart() {
        super.onStart();
        IntentFilter f = new IntentFilter();
        f.addAction(Intent.ACTION_PACKAGE_ADDED); f.addAction(Intent.ACTION_PACKAGE_REMOVED);
        f.addAction(Intent.ACTION_PACKAGE_CHANGED); f.addAction(Intent.ACTION_PACKAGE_REPLACED);
        f.addDataScheme("package");
        registerReceiver(packages, f, Context.RECEIVER_EXPORTED);
        registered = true;
    }

    @Override public void onStop() {
        if (registered) { unregisterReceiver(packages); registered = false; }
        super.onStop();
    }

    @Override public void onResume() { super.onResume(); loadApps(); }

    @Override public void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putString("query", query); out.putBoolean("favoritesOnly", favoritesOnly);
        out.putString("selected", selectedKey());
    }

    @Override public void onDestroy() {
        closed = true; loadGeneration++; wallpaperGeneration++;
        if (registered) unregisterReceiver(packages);
        loader.shutdownNow(); images.shutdownNow(); main.removeCallbacksAndMessages(null);
        cache.evictAll(); super.onDestroy();
    }

    private int dp(float n) { return Math.round(n * getResources().getDisplayMetrics().density); }
    private GradientDrawable shape(int color, int stroke) {
        GradientDrawable d = new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(14));
        if (stroke != 0) d.setStroke(dp(2), stroke);
        return d;
    }
    private StateListDrawable focusBackground() {
        StateListDrawable d = new StateListDrawable();
        d.addState(new int[]{android.R.attr.state_focused}, shape(Color.rgb(51, 67, 87), accent));
        d.addState(new int[]{android.R.attr.state_pressed}, shape(Color.rgb(51, 67, 87), accent));
        d.addState(new int[]{}, shape(surface, 0)); return d;
    }
    private TextView label(String value, int size, int color) {
        TextView t = new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(color);
        t.setFontFeatureSettings("kern"); return t;
    }
    private TextView button(String title, View.OnClickListener click) {
        TextView b = label(title, 14, text); b.setGravity(Gravity.CENTER);
        b.setPadding(dp(20), 0, dp(20), 0); b.setFocusable(true); b.setClickable(true);
        b.setBackground(focusBackground()); b.setOnClickListener(click);
        b.setId(View.generateViewId()); return b;
    }

    private void buildUi() {
        boolean blue = prefs.getBoolean("blue", false);
        bg = Color.parseColor(blue ? "#142033" : "#101416");
        surface = Color.parseColor(blue ? "#243248" : "#23292D");
        text = Color.parseColor("#F1F3F4"); muted = Color.parseColor("#B7C0C8");
        accent = Color.parseColor("#A8C7FA");
        getWindow().setStatusBarColor(bg); getWindow().setNavigationBarColor(bg);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_NOTHING);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(44), dp(26), dp(44), dp(14));
        LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL);
        TextView title = label("Aplikasi", 30, text);
        header.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1));
        TextView brand = label("B866F GTV Project", 14, muted);
        header.addView(brand); root.addView(header);
        LinearLayout toolbar = new LinearLayout(this); toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setPadding(0, dp(14), 0, dp(18));
        TextView find = button("Cari", v -> openSearch());
        toolbar.addView(find, new LinearLayout.LayoutParams(dp(100), dp(44)));
        filterButton = button("Semua", v -> { favoritesOnly = !favoritesOnly; applyFilter(null); });
        addTool(toolbar, filterButton);
        sortButton = button(sortTitle(), v -> chooseSort()); addTool(toolbar, sortButton);
        TextView options = button("Tampilan", v -> appearance()); addTool(toolbar, options);
        TextView hiddenButton = button("Tersembunyi", v -> manageHidden()); addTool(toolbar, hiddenButton);
        root.addView(toolbar);
        grid = new GridView(this); grid.setId(View.generateViewId()); grid.setNumColumns(columns);
        grid.setHorizontalSpacing(dp(14)); grid.setVerticalSpacing(dp(5));
        grid.setStretchMode(GridView.STRETCH_COLUMN_WIDTH); grid.setSelector(android.R.color.transparent);
        grid.setVerticalScrollBarEnabled(false); grid.setHorizontalScrollBarEnabled(false);
        grid.setClipToPadding(false); grid.setPadding(dp(3), dp(3), dp(3), dp(10));
        grid.setClipChildren(false);
        grid.setDescendantFocusability(ViewGroup.FOCUS_BLOCK_DESCENDANTS);
        grid.setAdapter(adapter);
        grid.setOnFocusChangeListener((v, hasFocus) -> {
            for (int i = 0; i < grid.getChildCount(); i++)
                if (grid.getChildAt(i) instanceof Tile) ((Tile)grid.getChildAt(i)).updateSelection();
        });
        grid.setOnItemClickListener((parent, view, pos, id) -> { if (pos < visible.size()) launch(visible.get(pos)); });
        grid.setOnItemLongClickListener((parent, view, pos, id) -> {
            if (pos < visible.size()) appMenu(visible.get(pos)); return true;
        });
        grid.setOnKeyListener((v, code, event) -> {
            if (code == KeyEvent.KEYCODE_MENU && event.getAction() == KeyEvent.ACTION_DOWN) {
                int pos = grid.getSelectedItemPosition();
                if (pos >= 0 && pos < visible.size()) appMenu(visible.get(pos)); return true;
            }
            return false;
        });
        // Allow tile zoom inside the grid, but clip all scrolling content at the
        // viewport boundary so offscreen rows cannot cover the toolbar/footer.
        FrameLayout viewport = new FrameLayout(this);
        viewport.setClipChildren(true);
        viewport.addOnLayoutChangeListener((v, left, top, right, bottom, oldLeft, oldTop, oldRight, oldBottom) ->
            v.setClipBounds(new Rect(0, 0, right - left, bottom - top)));
        viewport.addView(grid, new FrameLayout.LayoutParams(-1, -1));
        root.addView(viewport, new LinearLayout.LayoutParams(-1, 0, 1));
        status = label("Memuat aplikasi…", 13, muted); status.setPadding(0, dp(10), 0, 0);
        root.addView(status, new LinearLayout.LayoutParams(-1, dp(34)));
        FrameLayout backdrop = new FrameLayout(this); backdrop.setBackgroundColor(bg);
        wallpaperView = new ImageView(this); wallpaperView.setScaleType(ImageView.ScaleType.CENTER_CROP);
        wallpaperView.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        backdrop.addView(wallpaperView, new FrameLayout.LayoutParams(-1, -1));
        wallpaperShade = new View(this); wallpaperShade.setBackgroundColor(Color.BLACK);
        wallpaperShade.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        wallpaperShade.setAlpha(wallpaperDim() / 100f);
        backdrop.addView(wallpaperShade, new FrameLayout.LayoutParams(-1, -1));
        backdrop.addView(root, new FrameLayout.LayoutParams(-1, -1));
        showWallpaper(wallpaperBitmap);
        setContentView(backdrop); find.requestFocus();
        grid.setNextFocusUpId(find.getId());
        for (int i = 0; i < toolbar.getChildCount(); i++) toolbar.getChildAt(i).setNextFocusDownId(grid.getId());
    }
    private void addTool(LinearLayout row, View b) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, dp(44));
        lp.leftMargin = dp(10); row.addView(b, lp);
    }
    private void loadApps() {
        if (closed) return;
        final int generation = ++loadGeneration;
        final String key = restoreKey != null ? restoreKey : selectedKey(); restoreKey = null;
        loader.execute(() -> {
            final List<Entry> found = new ArrayList<>();
            try {
                PackageManager pm = getPackageManager();
                LinkedHashMap<String, Entry> byPackage = new LinkedHashMap<>();
                for (String category : new String[]{Intent.CATEGORY_LEANBACK_LAUNCHER, Intent.CATEGORY_LAUNCHER}) {
                    Intent i = new Intent(Intent.ACTION_MAIN).addCategory(category);
                    for (ResolveInfo ri : pm.queryIntentActivities(i, 0)) {
                        String pkg = ri.activityInfo.packageName;
                        if (!pkg.equals(getPackageName()) && !pkg.equals("com.ebsproject.drawer")
                            && !byPackage.containsKey(pkg) && ri.activityInfo.enabled && ri.activityInfo.exported)
                            byPackage.put(pkg, new Entry(ri, pm));
                    }
                }
                found.addAll(byPackage.values());
            } catch (RuntimeException ex) {
                main.post(() -> { if (!closed) toast("Daftar aplikasi belum dapat dimuat. Coba buka kembali."); });
                return;
            }
            main.post(() -> {
                if (closed || generation != loadGeneration) return;
                all.clear(); all.addAll(found); applyFilter(key);
            });
        });
    }
    private String selectedKey() {
        if (grid == null) return null;
        int i = grid.getSelectedItemPosition();
        return i >= 0 && i < visible.size() ? visible.get(i).key : null;
    }
    private void applyFilter(String selected) {
        visible.clear(); String q = query.trim().toLowerCase(Locale.ROOT);
        for (Entry e : all) {
            if (hidden.contains(e.key) || (favoritesOnly && !favorites.contains(e.key))) continue;
            if (!q.isEmpty() && !e.label.toLowerCase(Locale.ROOT).contains(q)) continue;
            visible.add(e);
        }
        final Collator collator = Collator.getInstance(new Locale("id", "ID"));
        Collections.sort(visible, new Comparator<Entry>() {
            @Override public int compare(Entry a, Entry b) {
                int f = Boolean.compare(favorites.contains(b.key), favorites.contains(a.key));
                if (f != 0) return f;
                if (sort == 2) {
                    int c = Long.compare(prefs.getLong("last:" + b.key, 0), prefs.getLong("last:" + a.key, 0));
                    if (c != 0) return c;
                }
                int c = collator.compare(a.label, b.label);
                if (c == 0) c = a.key.compareTo(b.key);
                return sort == 1 ? -c : c;
            }
        });
        adapter.notifyDataSetChanged();
        filterButton.setText(favoritesOnly ? "Favorit" : "Semua"); sortButton.setText(sortTitle());
        String count = visible.size() + " aplikasi";
        if (!query.isEmpty()) count += " · Cari: " + query;
        if (visible.isEmpty()) count += favoritesOnly ? " · Tahan OK pada aplikasi untuk menambah favorit" : " · Coba ubah pencarian atau lihat Tersembunyi";
        else count += " · OK untuk buka · Tahan OK / Menu untuk opsi";
        status.setText(count);
        if (selected != null) for (int i = 0; i < visible.size(); i++)
            if (visible.get(i).key.equals(selected)) { grid.setSelection(i); break; }
    }
    private String sortTitle() { return new String[]{"Urut: A–Z", "Urut: Z–A", "Urut: Terakhir dibuka"}[sort]; }
    private AlertDialog.Builder dialog(String title) { return new AlertDialog.Builder(this).setTitle(title); }
    private void chooseSort() {
        dialog("Urutkan aplikasi").setSingleChoiceItems(new String[]{"Nama A–Z", "Nama Z–A", "Terakhir dibuka dari drawer ini"}, sort,
            (d, i) -> { String key = selectedKey(); sort = i; prefs.edit().putInt("sort", i).apply(); applyFilter(key); d.dismiss(); })
            .setNegativeButton("Batal", null).show();
    }
    private void openSearch() {
        search = new EditText(this); search.setSingleLine(true); search.setText(query);
        search.setTextColor(text); search.setHintTextColor(muted); search.setHint("Nama aplikasi");
        LinearLayout wrap = new LinearLayout(this); wrap.setPadding(dp(24), dp(8), dp(24), dp(4));
        wrap.addView(search, new LinearLayout.LayoutParams(-1, dp(52)));
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) { query = s.toString(); applyFilter(null); }
            public void afterTextChanged(Editable e) {}
        });
        AlertDialog d = dialog("Cari aplikasi").setView(wrap).setPositiveButton("Selesai", null)
            .setNeutralButton("Hapus pencarian", (which, id) -> { query = ""; applyFilter(null); }).create();
        d.setOnDismissListener(which -> {
            if (search != null) ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(search.getWindowToken(), 0);
            if (!visible.isEmpty()) { grid.requestFocus(); grid.setSelection(0); }
        });
        d.show(); search.requestFocus(); search.setSelection(search.length());
    }
    private void appearance() {
        String[] choices = {"Kolom: " + columns, "Gambar: " + (banners ? "Banner TV" : "Ikon aplikasi"),
            "Tema: " + (prefs.getBoolean("blue", false) ? "Biru malam" : "Gelap"), "Wallpaper",
            "Animasi fokus: " + (prefs.getBoolean("animations", true) ? "Aktif" : "Nonaktif"),
            "Pulihkan aplikasi tersembunyi", "Reset tampilan dan daftar favorit"};
        dialog("Tampilan drawer").setItems(choices, (d, n) -> {
            if (n == 0) {
                dialog("Jumlah kolom").setSingleChoiceItems(new String[]{"5 · Besar", "6 · Sedang", "7 · Ringkas"}, columns - 5,
                    (x, v) -> { columns = v + 5; prefs.edit().putInt("columns", columns).apply(); grid.setNumColumns(columns); adapter.notifyDataSetChanged(); x.dismiss(); })
                    .setNegativeButton("Batal", null).show();
            } else if (n == 1) {
                banners = !banners; prefs.edit().putBoolean("banners", banners).apply(); cache.evictAll(); adapter.notifyDataSetChanged();
            } else if (n == 2) {
                prefs.edit().putBoolean("blue", !prefs.getBoolean("blue", false)).apply(); restoreKey = selectedKey(); buildUi(); applyFilter(restoreKey);
            } else if (n == 3) wallpaperMenu();
            else if (n == 4) {
                prefs.edit().putBoolean("animations", !prefs.getBoolean("animations", true)).apply();
                for (int i = 0; i < grid.getChildCount(); i++)
                    if (grid.getChildAt(i) instanceof Tile) ((Tile)grid.getChildAt(i)).updateSelection(true);
            } else if (n == 5) manageHidden();
            else dialog("Reset pengaturan drawer?").setMessage("Favorit, aplikasi tersembunyi, pencarian, wallpaper, dan tampilan drawer ini akan direset. Aplikasi terpasang tetap ada.")
                .setNegativeButton("Batal", null).setPositiveButton("Reset", (x, v) -> {
                    clearDrawerWallpaper();
                    prefs.edit().clear().apply(); favorites.clear(); hidden.clear(); query = ""; favoritesOnly = false;
                    columns = 7; sort = 0; banners = true;
                    prefs.edit().putBoolean("compactTiles", true).putBoolean("wallpaperEnabled", false).apply();
                    cache.evictAll(); buildUi(); applyFilter(null);
                }).show();
        }).setNegativeButton("Tutup", null).show();
    }

    private File wallpaperFile() { return new File(getFilesDir(), "wallpaper.jpg"); }
    private int wallpaperDim() { return Math.max(35, Math.min(75, prefs.getInt("wallpaperDim", 55))); }
    private void showWallpaper(Bitmap bitmap) {
        wallpaperBitmap = bitmap; wallpaperView.setImageBitmap(bitmap);
        wallpaperShade.setVisibility(bitmap == null ? View.GONE : View.VISIBLE);
    }
    private Bitmap decodeWallpaper(File file) throws IOException {
        return ImageDecoder.decodeBitmap(ImageDecoder.createSource(file), (decoder, info, source) -> {
            int w = info.getSize().getWidth(), h = info.getSize().getHeight();
            if (w < 1 || h < 1 || w > 32768 || h > 32768 || (long)w * h > 200000000L)
                throw new IllegalArgumentException("Image dimensions too large");
            double ratio = Math.min(1d, Math.min(1920d / w, 1080d / h));
            decoder.setTargetSize(Math.max(1, (int)Math.round(w * ratio)), Math.max(1, (int)Math.round(h * ratio)));
            decoder.setAllocator(ImageDecoder.ALLOCATOR_SOFTWARE);
        });
    }
    private void loadWallpaper() {
        final int generation = ++wallpaperGeneration;
        loader.execute(() -> {
            if (!prefs.getBoolean("wallpaperEnabled", false)) { new AtomicFile(wallpaperFile()).delete(); return; }
            if (!wallpaperFile().exists()) return;
            try {
                // Recover an interrupted AtomicFile write before decoding the normalized copy.
                new AtomicFile(wallpaperFile()).openRead().close();
                final Bitmap bitmap = decodeWallpaper(wallpaperFile());
                main.post(() -> { if (!closed && generation == wallpaperGeneration) showWallpaper(bitmap); });
            } catch (IOException | RuntimeException ignored) {
                main.post(() -> { if (!closed && generation == wallpaperGeneration) toast("Wallpaper tidak dapat dibaca. Pilih gambar lain melalui Tampilan."); });
            }
        });
    }
    private void clearDrawerWallpaper() {
        prefs.edit().putBoolean("wallpaperEnabled", false).apply();
        ++wallpaperGeneration; showWallpaper(null);
        loader.execute(() -> new AtomicFile(wallpaperFile()).delete());
    }
    private void wallpaperMenu() {
        dialog("Wallpaper drawer").setItems(new String[]{"Pilih gambar", "Gelapkan wallpaper: " + wallpaperDim() + "%", "Hapus wallpaper"}, (d, n) -> {
            if (n == 0) chooseWallpaper();
            else if (n == 1) dialog("Kegelapan wallpaper").setSingleChoiceItems(new String[]{"35% · Lebih terang", "55% · Seimbang", "75% · Lebih gelap"},
                (wallpaperDim() - 35) / 20, (x, v) -> {
                    int dim = 35 + v * 20; prefs.edit().putInt("wallpaperDim", dim).apply(); wallpaperShade.setAlpha(dim / 100f); x.dismiss();
                }).setNegativeButton("Batal", null).show();
            else dialog("Hapus wallpaper drawer?").setMessage("Menghapus salinan wallpaper dalam drawer. File gambar asli tetap tersedia.")
                .setNegativeButton("Batal", null).setPositiveButton("Hapus", (x, v) -> clearDrawerWallpaper()).show();
        }).setNegativeButton("Tutup", null).show();
    }
    private void chooseWallpaper() {
        if (importingWallpaper) { toast("Gambar masih diproses"); return; }
        Intent pick = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*").addCategory(Intent.CATEGORY_OPENABLE);
        List<ResolveInfo> handlers = imagePickers(pick);
        if (handlers.isEmpty()) {
            pick.setAction(Intent.ACTION_GET_CONTENT); handlers = imagePickers(pick);
        }
        if (handlers.isEmpty()) { toast("Pasang pengelola berkas yang mendukung pemilihan gambar"); return; }
        final Intent request = pick.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION).putExtra(Intent.EXTRA_LOCAL_ONLY, true);
        final List<ResolveInfo> options = handlers;
        if (options.size() == 1) openPicker(request, options.get(0));
        else {
            String[] names = new String[options.size()];
            for (int i = 0; i < names.length; i++) names[i] = getPackageManager().getApplicationLabel(options.get(i).activityInfo.applicationInfo).toString();
            dialog("Pilih pengelola berkas").setItems(names, (d, n) -> openPicker(request, options.get(n))).setNegativeButton("Batal", null).show();
        }
    }
    private List<ResolveInfo> imagePickers(Intent request) {
        List<ResolveInfo> real = new ArrayList<>();
        for (ResolveInfo ri : getPackageManager().queryIntentActivities(request, PackageManager.MATCH_DEFAULT_ONLY))
            if (ri.activityInfo.exported && ri.activityInfo.enabled && !ri.activityInfo.packageName.contains("frameworkpackagestubs")) real.add(ri);
        return real;
    }
    private void openPicker(Intent request, ResolveInfo ri) {
        request.setComponent(new ComponentName(ri.activityInfo.packageName, ri.activityInfo.name));
        try { startActivityForResult(request, PICK_WALLPAPER); }
        catch (RuntimeException ex) { toast("Pemilih gambar tidak dapat dibuka"); }
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != PICK_WALLPAPER || result != RESULT_OK || data == null) return;
        final Uri uri = data.getData();
        if (uri == null) { toast("Tidak ada gambar yang dipilih"); return; }
        importingWallpaper = true; final int generation = ++wallpaperGeneration;
        toast("Memproses wallpaper…");
        loader.execute(() -> {
            File temp = null; FileOutputStream destination = null; AtomicFile saved = new AtomicFile(wallpaperFile());
            try {
                temp = File.createTempFile("wallpaper-", ".image", getCacheDir());
                try (InputStream in = getContentResolver().openInputStream(uri); FileOutputStream out = new FileOutputStream(temp)) {
                    if (in == null) throw new IOException("No image stream");
                    byte[] buffer = new byte[16384]; int count, total = 0;
                    while ((count = in.read(buffer)) != -1) {
                        total += count;
                        if (total > 32 * 1024 * 1024 || closed || generation != wallpaperGeneration) throw new IOException("Import limit or cancellation");
                        out.write(buffer, 0, count);
                    }
                }
                final Bitmap bitmap = decodeWallpaper(temp);
                if (closed || generation != wallpaperGeneration) return;
                destination = saved.startWrite();
                if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 92, destination)) throw new IOException("Cannot save image");
                saved.finishWrite(destination); destination = null;
                main.post(() -> {
                    if (!closed && generation == wallpaperGeneration) {
                        prefs.edit().putBoolean("wallpaperEnabled", true).apply(); showWallpaper(bitmap); toast("Wallpaper diterapkan");
                    }
                });
            } catch (IOException | RuntimeException ex) {
                if (destination != null) saved.failWrite(destination);
                main.post(() -> { if (!closed && generation == wallpaperGeneration) toast("Gambar tidak dapat dibaca atau melebihi 32 MB. Pilih JPG, PNG, atau WebP lain."); });
            } finally {
                if (temp != null) temp.delete();
                main.post(() -> { if (!closed) importingWallpaper = false; });
            }
        });
    }
    private void manageHidden() {
        final List<Entry> entries = new ArrayList<>();
        for (Entry e : all) if (hidden.contains(e.key)) entries.add(e);
        if (entries.isEmpty()) { toast("Tidak ada aplikasi tersembunyi"); return; }
        Collections.sort(entries, (a, b) -> a.label.compareToIgnoreCase(b.label));
        String[] names = new String[entries.size()];
        for (int i = 0; i < names.length; i++) names[i] = entries.get(i).label;
        final Set<String> restore = new HashSet<>();
        dialog("Pilih aplikasi untuk ditampilkan kembali").setMultiChoiceItems(names, new boolean[names.length], (d, n, checked) -> {
            if (checked) restore.add(entries.get(n).key); else restore.remove(entries.get(n).key);
        }).setNegativeButton("Batal", null).setPositiveButton("Tampilkan", (d, n) -> {
            hidden.removeAll(restore); saveLists(); applyFilter(null);
        }).show();
    }
    private void saveLists() { prefs.edit().putStringSet("favorites", new HashSet<>(favorites)).putStringSet("hidden", new HashSet<>(hidden)).apply(); }
    private void appMenu(final Entry e) {
        dialog(e.label).setItems(new String[]{"Buka", favorites.contains(e.key) ? "Hapus dari favorit" : "Tambahkan ke favorit", "Sembunyikan dari drawer", "Info aplikasi"},
            (d, n) -> {
                if (n == 0) launch(e);
                else if (n == 1) { if (!favorites.remove(e.key)) favorites.add(e.key); saveLists(); applyFilter(e.key); }
                else if (n == 2) dialog("Sembunyikan " + e.label + "?")
                    .setMessage("Hanya disembunyikan dari drawer ini. Pulihkan melalui tombol Tersembunyi.")
                    .setNegativeButton("Batal", null).setPositiveButton("Sembunyikan", (x, v) -> { hidden.add(e.key); saveLists(); applyFilter(null); }).show();
                else try { startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + e.component.getPackageName()))); }
                    catch (ActivityNotFoundException ex) { toast("Info aplikasi tidak tersedia"); }
            }).setNegativeButton("Tutup", null).show();
    }
    private void launch(Entry e) {
        try {
            Intent i = new Intent(Intent.ACTION_MAIN).setComponent(e.component).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i); prefs.edit().putLong("last:" + e.key, System.currentTimeMillis()).apply();
        } catch (RuntimeException ex) { toast("Aplikasi tidak dapat dibuka. Coba muat ulang drawer."); loadApps(); }
    }
    private void toast(String message) { Toast.makeText(this, message, Toast.LENGTH_SHORT).show(); }

    private final class AppsAdapter extends BaseAdapter {
        public int getCount() { return visible.size(); }
        public Entry getItem(int n) { return visible.get(n); }
        public long getItemId(int n) { return n; }
        @Override public View getView(int n, View reuse, ViewGroup parent) {
            final Tile tile = reuse instanceof Tile ? (Tile)reuse : new Tile();
            final Entry e = getItem(n); final boolean wantBanner = banners;
            tile.title.setText((favorites.contains(e.key) ? "★ " : "") + e.label);
            tile.setContentDescription(e.label + (favorites.contains(e.key) ? ", favorit" : ""));
            final String imageKey = e.key + (wantBanner ? ":banner" : ":icon");
            tile.image.setTag(imageKey); tile.image.setImageDrawable(null);
            Bitmap hit = cache.get(imageKey);
            if (hit != null) tile.image.setImageBitmap(hit);
            else if (!closed) images.execute(() -> {
                Bitmap bitmap = cache.get(imageKey);
                if (bitmap == null) bitmap = artwork(e, wantBanner);
                if (bitmap == null) return;
                final Bitmap ready = bitmap;
                if (!closed) cache.put(imageKey, ready);
                main.post(() -> { if (!closed && imageKey.equals(tile.image.getTag())) tile.image.setImageBitmap(ready); });
            });
            return tile;
        }
    }
    private Bitmap artwork(Entry e, boolean wantBanner) {
        try {
            PackageManager pm = getPackageManager(); Drawable d = null;
            if (wantBanner) {
                try { d = pm.getActivityBanner(e.component); } catch (PackageManager.NameNotFoundException ignored) {}
                if (d == null) try { d = pm.getApplicationBanner(e.component.getPackageName()); } catch (PackageManager.NameNotFoundException ignored) {}
            }
            boolean isBanner = d != null;
            if (d == null) d = pm.getActivityIcon(e.component);
            if (d == null) return null;
            int w = dp(180), h = dp(102); Bitmap b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(b);
            float maxW = isBanner ? w : dp(66), maxH = isBanner ? h : dp(66);
            int iw = Math.max(1, d.getIntrinsicWidth()), ih = Math.max(1, d.getIntrinsicHeight());
            float ratio = Math.min(maxW / iw, maxH / ih); int dw = Math.round(iw * ratio), dh = Math.round(ih * ratio);
            d.setBounds((w - dw)/2, (h - dh)/2, (w + dw)/2, (h + dh)/2); d.draw(canvas); return b;
        } catch (RuntimeException | PackageManager.NameNotFoundException ex) { return null; }
    }
    private final class Tile extends LinearLayout {
        final ImageView image;
        final TextView title;
        final GradientDrawable focusOutline;
        private ValueAnimator focusAnimator;
        private float focusProgress;
        private boolean focusInitialized, lastFocused;
        Tile() {
            super(DrawerActivity.this); setOrientation(VERTICAL); setPadding(dp(3), dp(3), dp(3), 0);
            setFocusable(false); setClipChildren(false); setClipToPadding(false);
            image = new ImageView(DrawerActivity.this); image.setScaleType(ImageView.ScaleType.FIT_CENTER);
            // Draw the focus border over the image instead of changing padding.
            // This keeps artwork geometry stable throughout focus changes.
            GradientDrawable cover = shape(surface, 0); cover.setCornerRadius(dp(6));
            image.setBackground(cover); image.setClipToOutline(true);
            focusOutline = shape(Color.TRANSPARENT, 0); focusOutline.setCornerRadius(dp(6));
            image.setForeground(focusOutline);
            addView(image, new LinearLayout.LayoutParams(-1, dp(60)));
            title = label("", 13, text); title.setGravity(Gravity.CENTER); title.setSingleLine(true);
            title.setEllipsize(TextUtils.TruncateAt.END); title.setPadding(dp(3), dp(4), dp(3), 0);
            title.setVisibility(INVISIBLE);
            addView(title, new LinearLayout.LayoutParams(-1, dp(22)));
            updateSelection();
        }
        @Override protected void onMeasure(int widthSpec, int heightSpec) {
            int width = MeasureSpec.getSize(widthSpec);
            image.getLayoutParams().height = Math.max(dp(32), Math.round((width - getPaddingLeft() - getPaddingRight()) * 9f / 16f));
            super.onMeasure(widthSpec, heightSpec);
        }
        private void updateSelection() {
            updateSelection(false);
        }
        private void updateSelection(boolean immediate) {
            if (image == null || title == null || focusOutline == null) return;
            boolean focused = isSelected() && grid.hasFocus();
            if (immediate || !focusInitialized || lastFocused != focused) {
                if (focusAnimator != null) focusAnimator.cancel();
                float target = focused ? 1f : 0f;
                if (immediate || !focusInitialized || !prefs.getBoolean("animations", true) || !ValueAnimator.areAnimatorsEnabled()) {
                    applyFocusProgress(target);
                } else {
                    // One progress value synchronizes the zoom, outline and label.
                    // Reversals start at the current value, without resetting scale.
                    focusAnimator = ValueAnimator.ofFloat(focusProgress, target);
                    focusAnimator.setDuration(180);
                    focusAnimator.setInterpolator(new DecelerateInterpolator(1.5f));
                    focusAnimator.addUpdateListener(a -> applyFocusProgress((Float)a.getAnimatedValue()));
                    focusAnimator.start();
                }
            }
            focusInitialized = true; lastFocused = focused;
        }
        private void applyFocusProgress(float progress) {
            focusProgress = progress;
            float scale = 1f + 0.04f * progress;
            image.setScaleX(scale); image.setScaleY(scale);
            focusOutline.setStroke(dp(2), (Math.round(255f * progress) << 24) | (accent & 0x00ffffff));
            title.setVisibility(VISIBLE); title.setAlpha(progress);
        }
        @Override protected void onDetachedFromWindow() {
            if (focusAnimator != null) focusAnimator.cancel();
            if (focusInitialized) applyFocusProgress(lastFocused ? 1f : 0f);
            focusInitialized = false;
            super.onDetachedFromWindow();
        }
        @Override public void setSelected(boolean selected) {
            super.setSelected(selected);
            updateSelection();
        }
    }
}
