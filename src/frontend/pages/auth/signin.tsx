import { getCsrfToken, getProviders, signIn } from "next-auth/react";
import { GetServerSidePropsContext } from "next";
import { FaGoogle, FaMapMarkedAlt } from 'react-icons/fa';

interface SignInProps {
  csrfToken: string;
  providers: Record<string, {
    id: string;
    name: string;
  }>;
}

export default function SignIn({ csrfToken, providers }: SignInProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-8 rounded-lg bg-white p-8 shadow-md">
        <div className="text-center">
          <FaMapMarkedAlt className="mx-auto h-12 w-12 text-primary-600" />
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Welcome to Locas
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Please sign in to continue
          </p>
        </div>
        
        <div className="mt-8 space-y-4">
          {Object.values(providers).map((provider) => (
            <div key={provider.id} className="w-full">
              {provider.id === 'google' && (
                <button
                  onClick={() => signIn(provider.id, { callbackUrl: '/' })}
                  className="btn btn-primary flex w-full items-center justify-center gap-2"
                >
                  <FaGoogle />
                  <span>Sign in with Google</span>
                </button>
              )}
            </div>
          ))}
        </div>
        
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            By signing in, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
    </div>
  );
}

export async function getServerSideProps(context: GetServerSidePropsContext) {
  const providers = await getProviders();
  const csrfToken = await getCsrfToken(context);
  return {
    props: {
      csrfToken: csrfToken || "",
      providers: providers || {},
    },
  };
}