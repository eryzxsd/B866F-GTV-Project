package com.local.gtvcompat;

import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.RemoteException;
import android.os.UserHandle;
import android.os.UserManager;
import android.util.Log;
import java.security.MessageDigest;
import java.util.Collections;
import java.util.List;

/** Read-only compatibility for firmware with no managed TV profiles. */
public final class TvProfileCompatService extends Service {
    private static final String DESCRIPTOR = "com.android.tv.profile.ITvProfileManager";
    private static final String LAUNCHER = "com.google.android.apps.tv.launcherx";
    private static final String GOOGLE_CERT = "5202f9072a0f75c831b2296428755df2548296947d11804e7579a934a5f700ae";
    private static final String TAG = "LocalTvProfileCompat";

    private void verifyLauncherCaller() {
        int uid = Binder.getCallingUid();
        PackageManager pm = getPackageManager();
        String[] packages = pm.getPackagesForUid(uid);
        boolean matches = false;
        if (packages != null) {
            for (String name : packages) if (LAUNCHER.equals(name)) matches = true;
        }
        if (!matches) throw new SecurityException("Only the installed Google TV Home may query this service");
        try {
            PackageInfo info = pm.getPackageInfo(LAUNCHER, PackageManager.GET_SIGNING_CERTIFICATES);
            for (Signature certificate : info.signingInfo.getApkContentsSigners()) {
                byte[] digest = MessageDigest.getInstance("SHA-256").digest(certificate.toByteArray());
                StringBuilder hex = new StringBuilder();
                for (byte value : digest) hex.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
                if (GOOGLE_CERT.equals(hex.toString())) return;
            }
        } catch (Exception error) {
            throw new SecurityException("Cannot verify Google TV caller", error);
        }
        throw new SecurityException("Unexpected Google TV signing certificate");
    }

    private void requireSingleNormalProfile() {
        long identity = Binder.clearCallingIdentity();
        try {
            UserManager users = (UserManager) getSystemService(USER_SERVICE);
            List<UserHandle> profiles = users.getUserProfiles();
            if (users.isManagedProfile() || profiles.size() != 1 ||
                !profiles.get(0).equals(android.os.Process.myUserHandle())) {
                throw new UnsupportedOperationException("Managed or additional Android profiles require the genuine TV profile service");
            }
        } finally {
            Binder.restoreCallingIdentity(identity);
        }
    }

    private final Binder binder = new Binder() {
        @Override protected boolean onTransact(int code, Parcel input, Parcel reply, int flags) throws RemoteException {
            if (code == IBinder.INTERFACE_TRANSACTION) {
                reply.writeString(DESCRIPTOR);
                return true;
            }
            verifyLauncherCaller();
            input.enforceInterface(DESCRIPTOR);
            if (code == 3) {
                input.enforceNoDataAvail();
                requireSingleNormalProfile();
                reply.writeNoException();
                reply.writeTypedList(Collections.<UserHandle>emptyList());
                Log.i(TAG, "Read-only query: no managed TV profiles on this single-profile firmware");
                return true;
            }
            if (code == 5) {
                int present = input.readInt();
                if (present != 1) throw new UnsupportedOperationException("A current-user handle is required");
                int requestedUser = input.readInt();
                IBinder callback = input.readStrongBinder();
                input.enforceNoDataAvail();
                requireSingleNormalProfile();
                if (requestedUser != 0 && requestedUser != -2) {
                    throw new UnsupportedOperationException("Cross-user switching is unsupported");
                }
                // Owner/current is already active; no Android user or account is changed.
                if (callback != null) {
                    Parcel result = Parcel.obtain();
                    try {
                        result.writeInterfaceToken("com.android.tv.profile.ITvProfileCallback");
                        result.writeInt(0); // No result Bundle; caller only needs completion.
                        if (!callback.transact(1, result, null, IBinder.FLAG_ONEWAY)) {
                            throw new RemoteException("Current-user completion callback was not accepted");
                        }
                    } finally { result.recycle(); }
                }
                reply.writeNoException();
                reply.writeInt(1);
                Log.i(TAG, "Confirmed already-active owner/current user; no user switch performed");
                return true;
            }
            Log.w(TAG, "Unsupported transaction rejected: " + code);
            throw new UnsupportedOperationException("Only the read-only TV profile list query is supported");
        }
    };

    @Override public IBinder onBind(Intent intent) {
        if (intent == null || !DESCRIPTOR.equals(intent.getAction())) return null;
        requireSingleNormalProfile();
        return binder;
    }
}
