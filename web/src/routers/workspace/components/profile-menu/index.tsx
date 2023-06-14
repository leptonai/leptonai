import { useInject } from "@lepton-libs/di";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useNavigate } from "react-router-dom";
import { Avatar, Button, Dropdown } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Logout } from "@carbon/icons-react";
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
                icon: <CarbonIcon icon={<Logout />} />,
                label: (
                  <div
                    css={css`
                      margin-left: 8px;
                    `}
                  >
                    Logout
                  </div>
                ),
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
            icon={
              <Avatar
                css={css`
                  position: relative;
                  top: -1px;
                  margin-right: 4px;
                `}
                size={18}
                onError={() => true}
                src={
                  <img
                    src={
                      profileService.profile?.oauth?.user_metadata.avatar_url
                    }
                    alt="avatar"
                  />
                }
              >
                test
              </Avatar>
            }
          >
            {profileService.profile?.identification?.email}
          </Button>
        </Dropdown>
      ) : null}
    </>
  );
};
