import React from 'react';
import Profile from '../components/User/Profile';

// ── Tailwind-migrated (Phase 6) ──
const ProfilePage: React.FC = () => {
  return (
    <div data-style="tailwind" className="mx-auto w-full max-w-[1140px] px-3">
      <div className="mt-6">
        <Profile />
      </div>
    </div>
  );
};

export default ProfilePage;
