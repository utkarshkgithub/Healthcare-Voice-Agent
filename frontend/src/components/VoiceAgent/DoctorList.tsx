import { Star, Stethoscope, CalendarDays } from 'lucide-react';
import type { Doctor } from '../../utils/api';

interface DoctorListProps {
  doctors: Doctor[];
  busy: boolean;
  message: string | null;
  prediction: {
    condition: string;
    additionalSymptoms: string[];
    remedy: string;
  };
  onBook: (doctor: Doctor) => void;
}

/**
 * Triage result panel: what the pipeline concluded, and who the patient can
 * see next. Fed by the conversational graph, then by the specialist-mapping
 * pipeline (POST /run_langgraph).
 *
 * Every doctor card carries a real slot_id from the database, so booking
 * cannot pick a slot that was never offered.
 */
export function DoctorList({
  doctors,
  busy,
  message,
  prediction,
  onBook,
}: DoctorListProps) {
  if (busy) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-white/60">
        Finding specialists and open slots…
      </div>
    );
  }

  if (!prediction.condition && !doctors.length) return null;

  return (
    <div className="flex flex-col gap-3">
      {prediction.condition && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
          <h3 className="mb-2 text-sm font-semibold text-white/80">
            Triage summary
          </h3>
          <p className="text-sm text-white/70">
            Likely condition:{' '}
            <span className="font-medium text-white">{prediction.condition}</span>
          </p>
          {prediction.additionalSymptoms.length > 0 && (
            <p className="mt-1 text-xs text-white/55">
              Related symptoms: {prediction.additionalSymptoms.join(', ')}
            </p>
          )}
          {prediction.remedy && (
            <p className="mt-1 text-xs text-white/55">
              Immediate step: {prediction.remedy}
            </p>
          )}
        </div>
      )}

      {message && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-white/70">
          {message}
        </div>
      )}

      {doctors.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white/80">
            <Stethoscope size={16} />
            Specialists for your symptoms
          </h3>

      <ul className="flex flex-col gap-3">
        {doctors.map((doctor) => (
          <li
            key={doctor.doctor_id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-black/25 px-4 py-3"
          >
            <div className="flex flex-col gap-1">
              <span className="font-medium text-white">{doctor.name}</span>
              <span className="text-xs text-white/55">
                {doctor.specialization} · {doctor.hospital}
              </span>
              <span className="flex items-center gap-3 text-xs text-white/45">
                <span className="flex items-center gap-1">
                  <Star size={12} />
                  {doctor.rating.toFixed(1)}
                </span>
                <span className="flex items-center gap-1">
                  <CalendarDays size={12} />
                  {doctor.next_available_date} at {doctor.start_time}
                </span>
                <span>₹{doctor.fees}</span>
              </span>
            </div>

            <button
              type="button"
              onClick={() => onBook(doctor)}
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-400"
            >
              Book
            </button>
          </li>
        ))}
          </ul>
        </div>
      )}
    </div>
  );
}