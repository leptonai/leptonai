import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { FC, PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";

export const OAuthGuard: FC<PropsWithChildren> = ({ children }) => {
  const profileService = useInject(ProfileService);
  const href = window.location.href;
  if (!profileService.profile?.oauth) {
    return <Navigate to={`/login?callbackURL=${href}`} replace />;
  } else {
    return <>{children}</>;
  }
};

export const IdentificationGuard: FC<PropsWithChildren> = ({ children }) => {
  const profileService = useInject(ProfileService);
  if (
    !profileService.profile?.identification ||
    !profileService.profile.identification?.enable
  ) {
    return <Navigate to="/closebeta" replace />;
  } else {
    return <>{children}</>;
  }
};

export const WorkspaceGuard: FC<PropsWithChildren> = ({ children }) => {
  const profileService = useInject(ProfileService);
  if (
    !profileService.profile ||
    profileService.profile.authorized_workspaces.length === 0
  ) {
    return <Navigate to="/no-workspace" replace />;
  } else {
    return <>{children}</>;
  }
};
