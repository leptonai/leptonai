import { SignAsOther } from "@lepton-dashboard/components/signin-other";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { Button, Col } from "antd";
import { FC } from "react";
import { useNavigate } from "react-router-dom";

export const CloseBeta: FC = () => {
  useDocumentTitle("Close Beta");
  const profileService = useInject(ProfileService);
  const navigate = useNavigate();
  if (profileService.profile?.identification?.enable) {
    return (
      <SignAsOther
        buttons={
          <Col flex={1}>
            <Button
              block
              type="primary"
              onClick={() => navigate("/", { relative: "route" })}
            >
              Go to workspace
            </Button>
          </Col>
        }
        heading="Your account is now available"
      />
    );
  } else {
    return (
      <SignAsOther
        buttons={
          <Col flex={1}>
            <Button
              block
              type="primary"
              onClick={() => navigate("/waitlist", { relative: "route" })}
            >
              Join waitlist
            </Button>
          </Col>
        }
        heading="We are currently in closed beta"
        tips="Thank you for your interest"
      />
    );
  }
};
