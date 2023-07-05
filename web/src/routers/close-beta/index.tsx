import { SignAsOther } from "@lepton-dashboard/components/signin-other";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { FC } from "react";

export const CloseBeta: FC = () => {
  useDocumentTitle("Close Beta");
  const profileService = useInject(ProfileService);
  if (profileService.profile?.identification?.enable) {
    return <SignAsOther heading="Your account is now available" />;
  } else {
    return (
      <SignAsOther
        waitlist
        heading="We are currently in closed beta"
        tips="Thank you for your interest"
      />
    );
  }
};
