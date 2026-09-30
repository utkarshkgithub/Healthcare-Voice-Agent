import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { User, History, Droplet, Phone, Cake, IdCard, AlertCircle } from 'lucide-react';
import { patientApi, type PatientDetails, type MedicalHistory } from '../../utils/api';

interface PatientPanelProps {
  onHistoryLoaded?: (history: MedicalHistory) => void;
}

const HISTORY_FIELDS: { key: keyof MedicalHistory; label: string }[] = [
  { key: 'past_diagnoses', label: 'Past diagnoses' },
  { key: 'surgeries', label: 'Surgeries' },
  { key: 'hospital_admissions', label: 'Admissions' },
  { key: 'immunization_records', label: 'Immunizations' },
  { key: 'family_medical_history', label: 'Family history' },
  { key: 'lifestyle_factors', label: 'Lifestyle' },
];

/**
 * Patient profile and medical history.
 *
 * Both routes derive identity from the bearer token, so this renders nothing
 * unless the patient is signed in. History is surfaced here because the
 * triage pipeline is only as good as what it knows about the person: a
 * comorbidity changes what counts as routine.
 */
export function PatientPanel({ onHistoryLoaded }: PatientPanelProps) {
  const [details, setDetails] = useState<PatientDetails | null>(null);
  const [history, setHistory] = useState<MedicalHistory | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem('token')) return;

    let cancelled = false;

    patientApi.details().then((data) => {
      if (!cancelled) setDetails(data);
    }).catch(() => {
      // 401 means the token expired; the dashboard simply shows nothing.
      if (!cancelled) setError('Could not load your profile.');
    });

    patientApi.medicalHistory().then((data) => {
      if (cancelled) return;
      setHistory(data);
      onHistoryLoaded?.(data);
    }).catch(() => {
      /* a patient with no history record is normal, not an error */
    });

    return () => {
      cancelled = true;
    };
  }, [onHistoryLoaded]);

  if (error) {
    return (
      <div className="card-glass rounded-2xl p-5 flex items-center gap-2 text-sm text-foreground-subtle">
        <AlertCircle className="w-4 h-4" />
        {error}
      </div>
    );
  }

  if (!details) return null;

  const populated = history
    ? HISTORY_FIELDS.filter(({ key }) => history[key])
    : [];

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.25 }}
      className="space-y-4"
    >
      <div className="card-glass rounded-2xl p-5">
        <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
          <User className="w-5 h-5" />
          Your profile
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <Field icon={<IdCard className="w-3.5 h-3.5" />} label="MRN" value={details.medical_record_number} />
          <Field icon={<Cake className="w-3.5 h-3.5" />} label="Date of birth" value={details.date_of_birth} />
          <Field icon={<Droplet className="w-3.5 h-3.5" />} label="Blood group" value={details.blood_group} />
          <Field icon={<User className="w-3.5 h-3.5" />} label="Gender" value={details.gender} />
          <Field icon={<Phone className="w-3.5 h-3.5" />} label="Contact" value={details.contact_number} />
          <Field icon={<User className="w-3.5 h-3.5" />} label="Marital status" value={details.marital_status} />
        </div>
      </div>

      {populated.length > 0 && (
        <div className="card-glass rounded-2xl p-5">
          <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <History className="w-5 h-5" />
            Medical history
          </h2>
          <dl className="space-y-3 text-sm">
            {populated.map(({ key, label }) => (
              <div key={key}>
                <dt className="text-xs uppercase tracking-wide text-foreground-subtle">{label}</dt>
                <dd className="text-foreground mt-0.5">{history?.[key]}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </motion.section>
  );
}

function Field({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value?: string | null;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-foreground-subtle flex items-center gap-1">
        {icon}
        {label}
      </dt>
      <dd className="text-foreground mt-0.5">{value || '—'}</dd>
    </div>
  );
}