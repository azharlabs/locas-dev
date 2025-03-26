import React from 'react';
import { signIn, signOut, useSession } from 'next-auth/react';
import { FaGoogle } from 'react-icons/fa';

const LoginButton: React.FC = () => {
  const { data: session } = useSession();

  if (session && session.user) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 rounded-full bg-white px-2 py-1 shadow-sm">
          {session.user.image ? (
            <div className="relative h-8 w-8 overflow-hidden rounded-full">
              <img
                src={session.user.image}
                alt={session.user.name || 'User'}
                className="h-full w-full object-cover"
              />
            </div>
          ) : (
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-primary-800">
              {session.user.name?.charAt(0) || 'U'}
            </div>
          )}
          <span className="text-sm font-medium">{session.user.name}</span>
        </div>
        <button
          onClick={() => signOut()}
          className="btn btn-outline text-sm"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => signIn('google')}
      className="btn btn-primary flex items-center gap-2"
    >
      <FaGoogle />
      <span>Sign in with Google</span>
    </button>
  );
};

export default LoginButton;