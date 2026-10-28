import { useEffect, useId, useMemo, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { ProblemNotice, type Problem } from '../components/ProblemNotice';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { initials, timeZoneLabel } from '../lib/home';
import { UNREACHABLE, browserTimeZone } from '../lib/invite';
import {
  FIELD_ERRORS,
  buildPatch,
  fetchProfile,
  profileProblem,
  saveProfile,
  startingTimeZone,
  timeZoneOptions,
  toForm,
  type ContactPreference,
  type Profile,
  type ProfileForm,
} from '../lib/profile';

// "/me" (SCRUM-17): the signed-in person's own settings. P18 on desktop, X18 on phones.
// Changing the timezone sends the person back to "/" so every date there is read again in the
// new zone; RequireAuth re-reads who they are on each navigation, so nothing else is needed.

type State =
  { status: 'loading' } | { status: 'ready'; profile: Profile | null } | { status: 'error' };

const SECTION_TITLE = 'm-0 font-serif text-[18px] font-semibold leading-7 text-ink';

function Avatar({ name, url }: { name: string; url: string | null }) {
  const [failed, setFailed] = useState(false);
  if (url && !failed) {
    return (
      <img
        src={url}
        alt=""
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        className="h-16 w-16 shrink-0 rounded-full border border-line object-cover"
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-primary text-[20px] font-semibold text-primary-on"
    >
      {initials(name)}
    </span>
  );
}

function Check({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  const id = useId();
  return (
    <label htmlFor={id} className="flex cursor-pointer items-start gap-3">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 h-5 w-5 shrink-0 accent-primary"
      />
      <span>
        <span className="block text-[14px] font-semibold text-ink">{label}</span>
        <span className="block text-meta text-ink-meta">{hint}</span>
      </span>
    </label>
  );
}

function Switch({
  label,
  hint,
  on,
  onChange,
}: {
  label: string;
  hint: string;
  on: boolean;
  onChange: (on: boolean) => void;
}) {
  const labelId = useId();
  const hintId = useId();
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p id={labelId} className="m-0 text-[14px] font-semibold text-ink">
          {label}
        </p>
        <p id={hintId} className="m-0 mt-0.5 text-meta text-ink-meta">
          {hint}
        </p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-labelledby={labelId}
        aria-describedby={hintId}
        onClick={() => onChange(!on)}
        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors before:absolute before:-inset-2 before:content-[''] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
          on ? 'bg-primary' : 'bg-line'
        }`}
      >
        <span
          aria-hidden="true"
          className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-surface shadow transition-transform ${
            on ? 'translate-x-5' : ''
          }`}
        />
      </button>
    </div>
  );
}

function ProfileEditor({ profile }: { profile: Profile }) {
  const navigate = useNavigate();
  const [saved, setSaved] = useState(profile);
  const [startZone] = useState(() => startingTimeZone(profile.timezone, browserTimeZone()));
  const [form, setForm] = useState<ProfileForm>(() => ({
    ...toForm(profile),
    timezone: startZone,
  }));
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [badFields, setBadFields] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const zones = useMemo(() => timeZoneOptions(), []);

  function update<K extends keyof ProfileForm>(key: K, value: ProfileForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setNotice('');
  }

  const fieldError = (name: string) =>
    badFields.includes(name) ? (FIELD_ERRORS[name] ?? 'Check this field.') : '';

  const zoneHint =
    form.timezone === startZone && saved.timezone !== startZone
      ? `${timeZoneLabel(form.timezone)}. Detected from your browser; save to keep it.`
      : timeZoneLabel(form.timezone);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProblem(null);
    setBadFields([]);
    const patch = buildPatch(saved, form);
    if (Object.keys(patch).length === 0) {
      setNotice('Nothing to change.');
      return;
    }
    setNotice('');
    setSaving(true);
    try {
      const result = await saveProfile(patch);
      if (!result.ok) {
        setProblem(profileProblem(result.status));
        setBadFields(result.fields);
        return;
      }
      const zoneChanged = result.profile.timezone !== saved.timezone;
      setSaved(result.profile);
      setForm(toForm(result.profile));
      setNotice('Saved');
      if (zoneChanged) navigate('/');
    } catch {
      setProblem(UNREACHABLE);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="flex-1 px-4 pb-12 pt-6 lg:px-14 lg:pt-14">
      <div className="max-w-[720px]">
        <div className="flex items-center gap-4">
          <Avatar key={saved.photo_url ?? ''} name={saved.full_name} url={saved.photo_url} />
          <div className="min-w-0">
            <h1 className="m-0 truncate text-page-title tracking-[-0.01em]">{saved.full_name}</h1>
            <p className="m-0 truncate text-meta text-ink-meta">{saved.email}</p>
          </div>
        </div>
        <p className="m-0 mt-3 text-meta text-ink-meta">
          Your email cannot be changed here yet. Changing it will need a check that the new address
          is yours.
        </p>

        <form onSubmit={handleSubmit} noValidate className="mt-6 flex flex-col gap-4">
          <Card className="!p-6">
            <h2 className={SECTION_TITLE}>About you</h2>
            <div className="mt-4 grid gap-4">
              <Input
                label="Display name"
                value={form.full_name}
                onChange={(event) => update('full_name', event.target.value)}
                error={fieldError('full_name')}
                autoComplete="name"
              />
              <Input
                label="Photo link"
                value={form.photo_url}
                onChange={(event) => update('photo_url', event.target.value)}
                hint="A link to a picture, starting with https://. Uploading a photo comes later."
                error={fieldError('photo_url')}
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
              />
            </div>
          </Card>

          <Card className="!p-6">
            <h2 className={SECTION_TITLE}>Your timezone</h2>
            <div className="mt-4">
              <Input
                label="Timezone"
                list="timezones"
                value={form.timezone}
                onChange={(event) => update('timezone', event.target.value)}
                hint={zoneHint}
                error={fieldError('timezone')}
                autoComplete="off"
                spellCheck={false}
              />
              <datalist id="timezones">
                {zones.map((zone) => (
                  <option key={zone} value={zone} aria-label={zone} />
                ))}
              </datalist>
            </div>
          </Card>

          <Card className="!p-6">
            <h2 className={SECTION_TITLE}>How to reach you</h2>
            <div className="mt-4 grid gap-4">
              <Select
                label="Preferred way to be contacted"
                value={form.contact_preference}
                onChange={(event) =>
                  update('contact_preference', event.target.value as ContactPreference)
                }
                error={fieldError('contact_preference')}
              >
                <option value="email">Email</option>
                <option value="discord">Discord</option>
                <option value="phone">Phone</option>
              </Select>
              {form.contact_preference !== 'email' && (
                <Input
                  label={form.contact_preference === 'discord' ? 'Discord handle' : 'Phone number'}
                  value={form.contact_detail}
                  onChange={(event) => update('contact_detail', event.target.value)}
                  error={fieldError('contact_detail')}
                  autoComplete="off"
                />
              )}
            </div>
          </Card>

          <Card className="!p-6">
            <h2 className={SECTION_TITLE}>Email</h2>
            <p className="m-0 mt-2 text-body text-ink-body">
              Account emails such as password resets always send.
            </p>
            <div className="mt-4 flex flex-col gap-4">
              <Check
                label="New and reviewed work"
                hint="When work is assigned to you, reviewed or approved."
                checked={form.email_assignments}
                onChange={(checked) => update('email_assignments', checked)}
              />
              <Check
                label="Reminders"
                hint="When something is due soon."
                checked={form.email_reminders}
                onChange={(checked) => update('email_reminders', checked)}
              />
              <Check
                label="Weekly summary"
                hint="One email a week with where you stand."
                checked={form.email_digest}
                onChange={(checked) => update('email_digest', checked)}
              />
            </div>
          </Card>

          <Card className="!p-6">
            <h2 className={SECTION_TITLE}>Public byline</h2>
            <div className="mt-4">
              <Switch
                label="Show my name on my public byline"
                hint="Off by default. Your public byline page shows the same setting, so changing it here changes it there."
                on={form.public_byline_consent}
                onChange={(on) => update('public_byline_consent', on)}
              />
            </div>
          </Card>

          {problem && <ProblemNotice problem={problem} />}

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <Button type="submit" loading={saving} className="w-full lg:w-auto">
              Save changes
            </Button>
            {notice && (
              <p role="status" className="m-0 text-meta text-ink-body">
                {notice}
              </p>
            )}
          </div>
        </form>
      </div>
    </main>
  );
}

export default function ProfilePage() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let current = true;
    fetchProfile()
      .then((profile) => current && setState({ status: 'ready', profile }))
      .catch(() => current && setState({ status: 'error' }));
    return () => {
      current = false;
    };
  }, []);

  if (state.status === 'loading') return null;
  if (state.status === 'error') {
    return (
      <p role="alert" className="p-8 text-body text-ink">
        Your profile could not be loaded. Reload the page to try again.
      </p>
    );
  }
  if (!state.profile) {
    return (
      <main className="flex-1 px-4 py-10 lg:px-14">
        <h1 className="m-0 text-page-title">Your profile</h1>
        <p className="m-0 mt-2 text-body text-ink-body">
          You are not part of an organization yet. Use the invite link your supervisor emailed you.
        </p>
      </main>
    );
  }
  return <ProfileEditor profile={state.profile} />;
}
