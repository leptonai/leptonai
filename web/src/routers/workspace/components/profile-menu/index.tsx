import { useInject } from "@lepton-libs/di";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useNavigate } from "react-router-dom";
import { Button, Dropdown, Space } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ChevronDown, Logout } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { FC } from "react";

export const ProfileMenu: FC = () => {
  const profileService = useInject(ProfileService);
  const authService = useInject(AuthService);
  const navigate = useNavigate();
  return (
    <>
      {profileService.profile?.oauth?.id ? (
        <Dropdown
          menu={{
            items: [
              {
                icon: <Logout />,
                label: "Logout",
                key: "logout",
                onClick: () =>
                  authService.logout().then(() => {
                    navigate("/login", { relative: "route" });
                  }),
              },
            ],
          }}
        >
          <Button
            type="text"
            css={css`
              padding: 4px 6px;
            `}
          >
            <Space>
              {profileService.profile?.identification?.email}
              <CarbonIcon icon={<ChevronDown />} />
            </Space>
          </Button>
        </Dropdown>
      ) : (
        <Button
          type="text"
          size="small"
          icon={<CarbonIcon icon={<Logout />} />}
          onClick={() => {
            authService.logout().then(() => {
              navigate("/login", { relative: "route" });
            });
          }}
        >
          Logout
        </Button>
      )}
    </>
  );
};
